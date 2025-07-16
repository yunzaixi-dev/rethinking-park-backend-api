import asyncio
import uuid
import logging
import io
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from services.cache_service import CacheService
from services.enhanced_vision_service import enhanced_vision_service
from services.image_processing_service import image_processing_service
from services.label_analysis_service import label_analysis_service
from services.natural_element_analyzer import natural_element_analyzer
from services.image_annotation_service import image_annotation_service
from services.error_handling import (
    BatchProcessingException,
    ProcessingException,
    VisionAPIException,
    retry_processing,
    handle_batch_error,
    handle_processing_error
)

logger = logging.getLogger(__name__)

class BatchOperationType(str, Enum):
    """Batch operation types"""
    DETECT_OBJECTS = "detect_objects"
    EXTRACT_OBJECT = "extract_object"
    ANALYZE_LABELS = "analyze_labels"
    ANALYZE_NATURE = "analyze_nature"
    ANNOTATE_IMAGE = "annotate_image"

class BatchOperationStatus(str, Enum):
    """Batch operation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class BatchOperation:
    """Individual batch operation"""
    operation_id: str
    operation_type: BatchOperationType
    image_hash: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: BatchOperationStatus = BatchOperationStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    processing_time_ms: int = 0
    retry_count: int = 0
    max_retries: int = 2

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "image_hash": self.image_hash,
            "parameters": self.parameters,
            "status": self.status.value,
            "result": self.result,
            "error_message": self.error_message,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "processing_time_ms": self.processing_time_ms,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }

@dataclass
class BatchJob:
    """Batch processing job containing multiple operations"""
    batch_id: str
    operations: List[BatchOperation] = field(default_factory=list)
    status: BatchOperationStatus = BatchOperationStatus.PENDING
    created_time: datetime = field(default_factory=datetime.now)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    callback_url: Optional[str] = None
    max_concurrent_operations: int = 10
    total_operations: int = 0
    completed_operations: int = 0
    failed_operations: int = 0
    progress_percentage: float = 0.0

    def update_progress(self):
        """Update job progress based on operation statuses"""
        self.total_operations = len(self.operations)
        self.completed_operations = sum(1 for op in self.operations if op.status == BatchOperationStatus.COMPLETED)
        self.failed_operations = sum(1 for op in self.operations if op.status == BatchOperationStatus.FAILED)
        
        finished_operations = self.completed_operations + self.failed_operations
        self.progress_percentage = (finished_operations / self.total_operations * 100) if self.total_operations > 0 else 0.0
        
        # Update job status
        if finished_operations == self.total_operations:
            self.status = BatchOperationStatus.COMPLETED
            self.end_time = datetime.now()
        elif any(op.status == BatchOperationStatus.RUNNING for op in self.operations):
            self.status = BatchOperationStatus.RUNNING

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "batch_id": self.batch_id,
            "status": self.status.value,
            "created_time": self.created_time.isoformat(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "callback_url": self.callback_url,
            "max_concurrent_operations": self.max_concurrent_operations,
            "total_operations": self.total_operations,
            "completed_operations": self.completed_operations,
            "failed_operations": self.failed_operations,
            "progress_percentage": self.progress_percentage,
            "operations": [op.to_dict() for op in self.operations]
        }

class BatchProcessingService:
    """Service for managing batch processing operations"""
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        self.active_jobs: Dict[str, BatchJob] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self._lock = threading.Lock()
        
        # Operation handlers mapping
        self.operation_handlers = {
            BatchOperationType.DETECT_OBJECTS: self._handle_detect_objects,
            BatchOperationType.EXTRACT_OBJECT: self._handle_extract_object,
            BatchOperationType.ANALYZE_LABELS: self._handle_analyze_labels,
            BatchOperationType.ANALYZE_NATURE: self._handle_analyze_nature,
            BatchOperationType.ANNOTATE_IMAGE: self._handle_annotate_image,
        }
        
        # Statistics
        self.stats = {
            "total_jobs_created": 0,
            "total_jobs_completed": 0,
            "total_operations_processed": 0,
            "total_operations_failed": 0,
            "average_processing_time_ms": 0.0
        }
        
        logger.info("BatchProcessingService initialized")

    async def create_batch_job(
        self,
        operations: List[Dict[str, Any]],
        callback_url: Optional[str] = None,
        max_concurrent_operations: int = 10
    ) -> str:
        """
        Create a new batch processing job
        
        Args:
            operations: List of operation definitions
            callback_url: Optional callback URL for completion notification
            max_concurrent_operations: Maximum concurrent operations (max 10)
            
        Returns:
            batch_id: Unique identifier for the batch job
        """
        # Validate input
        if not operations:
            raise ValueError("Operations list cannot be empty")
        
        if len(operations) > 50:  # Reasonable limit
            raise ValueError("Too many operations in batch (max 50)")
        
        if max_concurrent_operations > 10:
            max_concurrent_operations = 10
        
        # Generate batch ID
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        
        # Create batch operations
        batch_operations = []
        for i, op_def in enumerate(operations):
            try:
                operation = self._create_batch_operation(op_def, i)
                batch_operations.append(operation)
            except Exception as e:
                logger.error(f"Failed to create operation {i}: {e}")
                raise ValueError(f"Invalid operation definition at index {i}: {str(e)}")
        
        # Create batch job
        batch_job = BatchJob(
            batch_id=batch_id,
            operations=batch_operations,
            callback_url=callback_url,
            max_concurrent_operations=max_concurrent_operations
        )
        
        # Store job
        with self._lock:
            self.active_jobs[batch_id] = batch_job
            self.stats["total_jobs_created"] += 1
        
        # Cache job status
        await self.cache_service.set_batch_processing_status(batch_id, batch_job.to_dict())
        
        logger.info(f"Created batch job {batch_id} with {len(batch_operations)} operations")
        return batch_id

    def _create_batch_operation(self, op_def: Dict[str, Any], index: int) -> BatchOperation:
        """Create a batch operation from definition"""
        required_fields = ["type", "image_hash"]
        for field in required_fields:
            if field not in op_def:
                raise ValueError(f"Missing required field '{field}' in operation definition")
        
        operation_type = op_def["type"]
        if operation_type not in [t.value for t in BatchOperationType]:
            raise ValueError(f"Invalid operation type: {operation_type}")
        
        operation_id = f"op_{uuid.uuid4().hex[:8]}_{index}"
        
        return BatchOperation(
            operation_id=operation_id,
            operation_type=BatchOperationType(operation_type),
            image_hash=op_def["image_hash"],
            parameters=op_def.get("parameters", {}),
            max_retries=op_def.get("max_retries", 2)
        )

    async def start_batch_job(self, batch_id: str) -> bool:
        """
        Start processing a batch job
        
        Args:
            batch_id: Batch job identifier
            
        Returns:
            bool: True if job started successfully
        """
        with self._lock:
            if batch_id not in self.active_jobs:
                logger.error(f"Batch job {batch_id} not found")
                return False
            
            batch_job = self.active_jobs[batch_id]
            if batch_job.status != BatchOperationStatus.PENDING:
                logger.warning(f"Batch job {batch_id} is not in pending status")
                return False
            
            batch_job.status = BatchOperationStatus.RUNNING
            batch_job.start_time = datetime.now()
        
        # Start processing operations asynchronously
        asyncio.create_task(self._process_batch_job(batch_id))
        
        logger.info(f"Started batch job {batch_id}")
        return True

    async def _process_batch_job(self, batch_id: str):
        """Process all operations in a batch job"""
        try:
            batch_job = self.active_jobs[batch_id]
            
            # Process operations with concurrency limit
            semaphore = asyncio.Semaphore(batch_job.max_concurrent_operations)
            
            async def process_operation_with_semaphore(operation: BatchOperation):
                async with semaphore:
                    await self._process_single_operation(batch_id, operation)
            
            # Create tasks for all operations
            tasks = [
                process_operation_with_semaphore(operation)
                for operation in batch_job.operations
            ]
            
            # Wait for all operations to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update final job status
            batch_job.update_progress()
            
            # Update cache
            await self.cache_service.set_batch_processing_status(batch_id, batch_job.to_dict())
            
            # Send callback notification if configured
            if batch_job.callback_url:
                await self._send_completion_callback(batch_job)
            
            # Update statistics
            with self._lock:
                self.stats["total_jobs_completed"] += 1
                self.stats["total_operations_processed"] += batch_job.completed_operations
                self.stats["total_operations_failed"] += batch_job.failed_operations
            
            logger.info(f"Completed batch job {batch_id}: {batch_job.completed_operations} successful, {batch_job.failed_operations} failed")
            
        except Exception as e:
            logger.error(f"Error processing batch job {batch_id}: {e}")
            # Mark job as failed
            if batch_id in self.active_jobs:
                self.active_jobs[batch_id].status = BatchOperationStatus.FAILED

    @retry_processing(max_attempts=1, base_delay=0.5)
    async def _process_single_operation(self, batch_id: str, operation: BatchOperation):
        """Process a single operation within a batch job with enhanced error handling"""
        operation.status = BatchOperationStatus.RUNNING
        operation.start_time = datetime.now()
        
        try:
            # Get operation handler
            handler = self.operation_handlers.get(operation.operation_type)
            if not handler:
                raise ProcessingException(
                    f"No handler for operation type: {operation.operation_type}",
                    operation="batch_operation_dispatch",
                    recoverable=False
                )
            
            # Execute operation with error handling
            start_time = time.time()
            result = await self._execute_operation_with_error_handling(
                handler, operation.image_hash, operation.parameters, operation.operation_id
            )
            end_time = time.time()
            
            # Update operation status
            operation.status = BatchOperationStatus.COMPLETED
            operation.result = result
            operation.processing_time_ms = int((end_time - start_time) * 1000)
            operation.end_time = datetime.now()
            
            logger.debug(f"Completed operation {operation.operation_id} in {operation.processing_time_ms}ms")
            
        except (VisionAPIException, ProcessingException) as e:
            # Handle specific processing errors with proper error recovery
            error_info = handle_processing_error(
                e, 
                operation.operation_type.value, 
                operation_id=operation.operation_id,
                image_hash=operation.image_hash,
                batch_id=batch_id
            )
            
            logger.error(f"Operation {operation.operation_id} failed with processing error: {error_info}")
            operation.status = BatchOperationStatus.FAILED
            operation.error_message = error_info.get("message", str(e))
            operation.end_time = datetime.now()
            
            # Retry logic for recoverable errors
            if (error_info.get("recoverable", False) and 
                operation.retry_count < operation.max_retries):
                operation.retry_count += 1
                operation.status = BatchOperationStatus.PENDING
                retry_delay = min(2 ** operation.retry_count, 10)  # Exponential backoff, max 10s
                logger.info(f"Retrying operation {operation.operation_id} (attempt {operation.retry_count + 1}) in {retry_delay}s")
                await asyncio.sleep(retry_delay)
                await self._process_single_operation(batch_id, operation)
            
        except Exception as e:
            # Handle unexpected errors
            error_info = handle_processing_error(
                e, 
                "batch_operation_execution", 
                operation_id=operation.operation_id,
                image_hash=operation.image_hash,
                batch_id=batch_id
            )
            
            logger.error(f"Operation {operation.operation_id} failed with unexpected error: {error_info}")
            operation.status = BatchOperationStatus.FAILED
            operation.error_message = error_info.get("message", str(e))
            operation.end_time = datetime.now()
            
            # Retry logic for unexpected errors (more conservative)
            if operation.retry_count < min(operation.max_retries, 1):  # Max 1 retry for unexpected errors
                operation.retry_count += 1
                operation.status = BatchOperationStatus.PENDING
                logger.info(f"Retrying operation {operation.operation_id} after unexpected error (attempt {operation.retry_count + 1})")
                await asyncio.sleep(2)  # Fixed delay for unexpected errors
                await self._process_single_operation(batch_id, operation)
        
        # Update job progress
        batch_job = self.active_jobs[batch_id]
        batch_job.update_progress()
        
        # Update cache periodically
        await self.cache_service.set_batch_processing_status(batch_id, batch_job.to_dict())

    async def _execute_operation_with_error_handling(
        self, 
        handler: Callable, 
        image_hash: str, 
        parameters: Dict[str, Any], 
        operation_id: str
    ) -> Dict[str, Any]:
        """Execute operation handler with comprehensive error handling"""
        try:
            result = await handler(image_hash, parameters)
            
            # Validate result structure
            if not isinstance(result, dict):
                raise ProcessingException(
                    f"Operation handler returned invalid result type: {type(result)}",
                    operation="result_validation",
                    recoverable=False
                )
            
            return result
            
        except (VisionAPIException, ProcessingException):
            # Re-raise known processing exceptions
            raise
        except Exception as e:
            # Wrap unknown exceptions
            raise ProcessingException(
                f"Operation execution failed: {str(e)}",
                operation="operation_handler_execution",
                recoverable=True
            )

    # Operation handlers
    async def _handle_detect_objects(self, image_hash: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle object detection operation"""
        confidence_threshold = parameters.get("confidence_threshold", 0.5)
        include_faces = parameters.get("include_faces", True)
        include_labels = parameters.get("include_labels", True)
        max_results = parameters.get("max_results", 50)
        
        result = await enhanced_vision_service.detect_objects_enhanced(
            image_hash=image_hash,
            confidence_threshold=confidence_threshold,
            include_faces=include_faces,
            include_labels=include_labels,
            max_results=max_results
        )
        
        return result

    async def _handle_extract_object(self, image_hash: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle object extraction operation"""
        if "bounding_box" not in parameters:
            raise ValueError("bounding_box parameter is required for extraction")
        
        # Get image content from storage first
        from services.storage_service import storage_service
        image_info = await storage_service.get_image_info(image_hash)
        if not image_info:
            raise ValueError(f"Image not found: {image_hash}")
        
        # Download image content
        from services.gcs_service import gcs_service
        image_content = await gcs_service.download_image(image_info.gcs_url)
        
        # Create bounding box object
        from models.image import BoundingBox
        bbox_data = parameters["bounding_box"]
        bounding_box = BoundingBox(**bbox_data)
        
        output_format = parameters.get("output_format", "PNG")
        add_padding = parameters.get("add_padding", 10)
        background_removal = parameters.get("background_removal", False)
        
        # Extract object using image processing service
        result = image_processing_service.extract_by_bounding_box(
            image_content=image_content,
            bounding_box=bounding_box,
            padding=add_padding,
            output_format=output_format,
            background_removal=background_removal
        )
        
        # Upload extracted image to GCS
        extracted_filename = f"extracted_{image_hash}_{uuid.uuid4().hex[:8]}.{output_format.lower()}"
        extracted_gcs_url = await gcs_service.upload_processed_image(
            result.extracted_image_bytes,
            extracted_filename
        )
        
        # Return result in expected format
        return {
            "extracted_image_url": extracted_gcs_url,
            "bounding_box": result.bounding_box.dict(),
            "original_size": result.original_size.dict(),
            "extracted_size": result.extracted_size.dict(),
            "processing_method": result.processing_method,
            "file_size": len(result.extracted_image_bytes),
            "format": output_format.lower()
        }

    async def _handle_analyze_labels(self, image_hash: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle label analysis operation"""
        # Get image content and labels first
        from services.storage_service import storage_service
        from services.vision_service import vision_service
        from services.gcs_service import gcs_service
        
        image_info = await storage_service.get_image_info(image_hash)
        if not image_info:
            raise ValueError(f"Image not found: {image_hash}")
        
        # Download image content
        image_content = await gcs_service.download_image(image_info.gcs_url)
        
        # Get labels from Vision API
        labels = await vision_service.detect_labels(image_content)
        
        # Filter labels based on confidence threshold
        confidence_threshold = parameters.get("confidence_threshold", 0.3)
        filtered_labels = [
            label for label in labels 
            if label.get("score", 0) >= confidence_threshold
        ]
        
        # Perform label-based analysis
        analysis_depth = parameters.get("analysis_depth", "basic")
        include_confidence = parameters.get("include_confidence", True)
        
        result = label_analysis_service.analyze_by_labels(
            labels=filtered_labels,
            image_content=image_content,
            analysis_depth=analysis_depth,
            include_confidence=include_confidence
        )
        
        return result

    async def _handle_analyze_nature(self, image_hash: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle natural elements analysis operation"""
        # Get image content first
        from services.storage_service import storage_service
        from services.vision_service import vision_service
        from services.gcs_service import gcs_service
        
        image_info = await storage_service.get_image_info(image_hash)
        if not image_info:
            raise ValueError(f"Image not found: {image_hash}")
        
        # Download image content
        image_content = await gcs_service.download_image(image_info.gcs_url)
        
        analysis_depth = parameters.get("analysis_depth", "comprehensive")
        
        result = await natural_element_analyzer.analyze_natural_elements(
            image_content=image_content,
            vision_client=vision_service.client,
            analysis_depth=analysis_depth
        )
        
        # Convert result to dict for serialization
        return result.dict() if hasattr(result, 'dict') else result

    async def _handle_annotate_image(self, image_hash: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle image annotation operation"""
        # Get image content and detection results first
        from services.storage_service import storage_service
        from services.gcs_service import gcs_service
        
        image_info = await storage_service.get_image_info(image_hash)
        if not image_info:
            raise ValueError(f"Image not found: {image_hash}")
        
        # Download image content
        image_content = await gcs_service.download_image(image_info.gcs_url)
        
        include_face_markers = parameters.get("include_face_markers", True)
        include_object_boxes = parameters.get("include_object_boxes", True)
        include_labels = parameters.get("include_labels", True)
        output_format = parameters.get("output_format", "png")
        confidence_threshold = parameters.get("confidence_threshold", 0.5)
        
        # Get detection results for annotation
        objects = []
        faces = []
        
        if include_object_boxes or include_labels:
            # Get enhanced detection results
            detection_result = await enhanced_vision_service.detect_objects_enhanced(
                image_hash=image_hash,
                confidence_threshold=confidence_threshold,
                include_faces=include_face_markers,
                include_labels=include_labels
            )
            objects = detection_result.get("objects", [])
            faces = detection_result.get("faces", [])
        
        # Render annotated image
        annotated_image_bytes = image_annotation_service.render_annotated_image(
            image_content=image_content,
            objects=objects if include_object_boxes else None,
            faces=faces if include_face_markers else None,
            include_labels=include_labels,
            annotation_style=parameters.get("annotation_style")
        )
        
        # Upload annotated image to GCS
        annotation_id = f"annotated_{image_hash}_{uuid.uuid4().hex[:8]}"
        annotated_filename = f"{annotation_id}.{output_format.lower()}"
        annotated_gcs_url = await gcs_service.upload_processed_image(
            annotated_image_bytes,
            annotated_filename
        )
        
        # Get annotation statistics
        annotation_stats = image_annotation_service.get_annotation_statistics(
            objects=objects,
            faces=faces
        )
        
        # Get image size
        from PIL import Image
        pil_image = Image.open(io.BytesIO(annotated_image_bytes))
        from models.image import ImageSize
        image_size = ImageSize(width=pil_image.width, height=pil_image.height)
        
        return {
            "annotated_image_url": annotated_gcs_url,
            "original_image_url": image_info.gcs_url,
            "annotation_stats": annotation_stats,
            "file_size": len(annotated_image_bytes),
            "format": output_format.lower(),
            "image_size": image_size.dict()
        }

    async def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a batch job
        
        Args:
            batch_id: Batch job identifier
            
        Returns:
            Dict containing batch job status or None if not found
        """
        # Try cache first
        cached_status = await self.cache_service.get_batch_processing_status(batch_id)
        if cached_status:
            return cached_status
        
        # Check active jobs
        with self._lock:
            if batch_id in self.active_jobs:
                batch_job = self.active_jobs[batch_id]
                status = batch_job.to_dict()
                # Update cache
                await self.cache_service.set_batch_processing_status(batch_id, status)
                return status
        
        return None

    async def cancel_batch_job(self, batch_id: str) -> bool:
        """
        Cancel a batch job
        
        Args:
            batch_id: Batch job identifier
            
        Returns:
            bool: True if job was cancelled successfully
        """
        with self._lock:
            if batch_id not in self.active_jobs:
                return False
            
            batch_job = self.active_jobs[batch_id]
            if batch_job.status in [BatchOperationStatus.COMPLETED, BatchOperationStatus.FAILED]:
                return False
            
            # Cancel pending operations
            for operation in batch_job.operations:
                if operation.status == BatchOperationStatus.PENDING:
                    operation.status = BatchOperationStatus.CANCELLED
            
            batch_job.status = BatchOperationStatus.CANCELLED
            batch_job.end_time = datetime.now()
        
        # Update cache
        await self.cache_service.set_batch_processing_status(batch_id, batch_job.to_dict())
        
        logger.info(f"Cancelled batch job {batch_id}")
        return True

    async def get_batch_results(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Get aggregated results from a completed batch job
        
        Args:
            batch_id: Batch job identifier
            
        Returns:
            Dict containing aggregated results or None if not found/not completed
        """
        batch_status = await self.get_batch_status(batch_id)
        if not batch_status or batch_status["status"] != BatchOperationStatus.COMPLETED.value:
            return None
        
        # Aggregate results by operation type
        results_by_type = {}
        successful_operations = []
        failed_operations = []
        
        for operation in batch_status["operations"]:
            op_type = operation["operation_type"]
            
            if operation["status"] == BatchOperationStatus.COMPLETED.value:
                successful_operations.append(operation)
                if op_type not in results_by_type:
                    results_by_type[op_type] = []
                results_by_type[op_type].append(operation["result"])
            elif operation["status"] == BatchOperationStatus.FAILED.value:
                failed_operations.append(operation)
        
        # Calculate summary statistics
        total_processing_time = sum(op["processing_time_ms"] for op in batch_status["operations"])
        
        aggregated_results = {
            "batch_id": batch_id,
            "summary": {
                "total_operations": batch_status["total_operations"],
                "successful_operations": len(successful_operations),
                "failed_operations": len(failed_operations),
                "success_rate": len(successful_operations) / batch_status["total_operations"] * 100,
                "total_processing_time_ms": total_processing_time,
                "average_processing_time_ms": total_processing_time / batch_status["total_operations"] if batch_status["total_operations"] > 0 else 0
            },
            "results_by_type": results_by_type,
            "successful_operations": successful_operations,
            "failed_operations": failed_operations,
            "batch_metadata": {
                "created_time": batch_status["created_time"],
                "start_time": batch_status["start_time"],
                "end_time": batch_status["end_time"],
                "callback_url": batch_status["callback_url"]
            }
        }
        
        return aggregated_results

    async def _send_completion_callback(self, batch_job: BatchJob):
        """Send completion callback notification"""
        try:
            import aiohttp
            
            callback_data = {
                "batch_id": batch_job.batch_id,
                "status": batch_job.status.value,
                "completed_operations": batch_job.completed_operations,
                "failed_operations": batch_job.failed_operations,
                "progress_percentage": batch_job.progress_percentage,
                "end_time": batch_job.end_time.isoformat() if batch_job.end_time else None
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    batch_job.callback_url,
                    json=callback_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Callback sent successfully for batch {batch_job.batch_id}")
                    else:
                        logger.warning(f"Callback failed for batch {batch_job.batch_id}: {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send callback for batch {batch_job.batch_id}: {e}")

    def get_service_statistics(self) -> Dict[str, Any]:
        """Get batch processing service statistics"""
        with self._lock:
            active_jobs_count = len(self.active_jobs)
            running_jobs = sum(1 for job in self.active_jobs.values() if job.status == BatchOperationStatus.RUNNING)
            
            return {
                **self.stats,
                "active_jobs_count": active_jobs_count,
                "running_jobs_count": running_jobs,
                "service_uptime": datetime.now().isoformat(),
                "supported_operations": [op.value for op in BatchOperationType]
            }

    async def cleanup_completed_jobs(self, max_age_hours: int = 24):
        """Clean up completed jobs older than specified age"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        jobs_to_remove = []
        
        with self._lock:
            for batch_id, job in self.active_jobs.items():
                if (job.status in [BatchOperationStatus.COMPLETED, BatchOperationStatus.FAILED, BatchOperationStatus.CANCELLED] and
                    job.end_time and job.end_time < cutoff_time):
                    jobs_to_remove.append(batch_id)
            
            for batch_id in jobs_to_remove:
                del self.active_jobs[batch_id]
        
        logger.info(f"Cleaned up {len(jobs_to_remove)} completed batch jobs")
        return len(jobs_to_remove)

# Global batch processing service instance
from services.cache_service import cache_service
batch_processing_service = BatchProcessingService(cache_service)