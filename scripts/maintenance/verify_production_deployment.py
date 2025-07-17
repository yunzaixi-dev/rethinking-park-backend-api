#!/usr/bin/env python3
"""
生产环境部署验证脚本
详细分析API状态和问题
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

class ProductionAPIVerifier:
    def __init__(self, base_url: str = "https://api.rethinkingpark.com"):
        self.base_url = base_url.rstrip('/')
        self.api_v1 = f"{self.base_url}/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RethinkingPark-Production-Verifier/1.0'
        })
        self.results = {
            'working': [],
            'broken': [],
            'warnings': []
        }
        
    def test_endpoint(self, name: str, method: str, url: str, payload: Dict = None, files: Dict = None) -> Dict:
        """测试单个端点"""
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=15)
            elif method.upper() == 'POST':
                if files:
                    response = self.session.post(url, files=files, timeout=15)
                else:
                    response = self.session.post(url, json=payload, timeout=15)
            else:
                return {'status': 'unsupported', 'details': f'Method {method} not supported'}
            
            result = {
                'name': name,
                'method': method,
                'url': url,
                'status_code': response.status_code,
                'status': 'success' if response.status_code == 200 else 'error',
                'response_time': response.elapsed.total_seconds(),
                'details': {}
            }
            
            # 尝试解析JSON响应
            try:
                result['response'] = response.json()
                if response.status_code != 200:
                    result['details']['error_message'] = result['response'].get('message', 'Unknown error')
                    result['details']['error_details'] = result['response'].get('details', {})
            except:
                result['response'] = response.text[:200] if response.text else 'No response body'
            
            return result
            
        except requests.exceptions.RequestException as e:
            return {
                'name': name,
                'method': method,
                'url': url,
                'status': 'connection_error',
                'details': {'exception': str(e)}
            }
        except Exception as e:
            return {
                'name': name,
                'method': method,
                'url': url,
                'status': 'unknown_error',
                'details': {'exception': str(e)}
            }
    
    def verify_basic_endpoints(self):
        """验证基础端点"""
        print("🔍 验证基础端点...")
        
        endpoints = [
            ("根路径", "GET", f"{self.base_url}/"),
            ("健康检查", "GET", f"{self.base_url}/health"),
            ("API统计", "GET", f"{self.api_v1}/stats"),
            ("详细健康检查", "GET", f"{self.api_v1}/health-detailed"),
        ]
        
        for name, method, url in endpoints:
            result = self.test_endpoint(name, method, url)
            
            if result['status'] == 'success':
                print(f"✅ {name}: 正常")
                self.results['working'].append(result)
                
                # 显示关键信息
                if 'response' in result and isinstance(result['response'], dict):
                    resp = result['response']
                    if 'version' in resp:
                        print(f"   版本: {resp['version']}")
                    if 'status' in resp:
                        print(f"   状态: {resp['status']}")
                        
            else:
                print(f"❌ {name}: 失败 (状态码: {result.get('status_code', 'N/A')})")
                self.results['broken'].append(result)
                
                if 'details' in result and 'error_message' in result['details']:
                    print(f"   错误: {result['details']['error_message']}")
    
    def verify_image_operations(self):
        """验证图片操作功能"""
        print("\n🔍 验证图片操作功能...")
        
        # 测试图片上传
        test_image_data = b"fake image data for testing"
        files = {'file': ('test.jpg', test_image_data, 'image/jpeg')}
        
        upload_result = self.test_endpoint(
            "图片上传", "POST", f"{self.api_v1}/upload", files=files
        )
        
        if upload_result['status'] == 'success':
            print("✅ 图片上传: 正常")
            self.results['working'].append(upload_result)
            
            # 获取上传的图片哈希
            image_hash = upload_result['response'].get('image_hash')
            if image_hash:
                print(f"   图片哈希: {image_hash}")
                
                # 测试图片相关操作
                image_operations = [
                    ("图片信息", "GET", f"{self.api_v1}/image/{image_hash}"),
                    ("重复检查", "GET", f"{self.api_v1}/check-duplicate/{image_hash}"),
                ]
                
                for name, method, url in image_operations:
                    result = self.test_endpoint(name, method, url)
                    
                    if result['status'] == 'success':
                        print(f"✅ {name}: 正常")
                        self.results['working'].append(result)
                    else:
                        print(f"❌ {name}: 失败")
                        self.results['broken'].append(result)
                
                # 测试图片分析（可能会失败，但要记录原因）
                analysis_tests = [
                    ("基础分析", {
                        "image_hash": image_hash,
                        "analysis_types": ["labels"]
                    }),
                    ("自然元素分析", {
                        "image_hash": image_hash,
                        "analysis_types": ["vegetation"]
                    })
                ]
                
                for name, payload in analysis_tests:
                    if name == "基础分析":
                        url = f"{self.api_v1}/analyze"
                    else:
                        url = f"{self.api_v1}/analyze-nature"
                    
                    result = self.test_endpoint(name, "POST", url, payload)
                    
                    if result['status'] == 'success':
                        print(f"✅ {name}: 正常")
                        self.results['working'].append(result)
                    else:
                        print(f"⚠️ {name}: 失败 (可能是配置问题)")
                        self.results['warnings'].append(result)
                        
                        if result.get('status_code') == 422:
                            print("   原因: 请求参数验证失败")
                        elif result.get('status_code') == 500:
                            print("   原因: 服务器内部错误 (可能是Vision API配置)")
                
                # 清理测试图片
                delete_result = self.test_endpoint(
                    "删除图片", "DELETE", f"{self.api_v1}/image/{image_hash}"
                )
                
                if delete_result['status'] == 'success':
                    print("✅ 图片删除: 正常")
                    self.results['working'].append(delete_result)
                else:
                    print("⚠️ 图片删除: 失败")
                    self.results['warnings'].append(delete_result)
            
        else:
            print("❌ 图片上传: 失败")
            self.results['broken'].append(upload_result)
    
    def verify_monitoring_endpoints(self):
        """验证监控端点"""
        print("\n🔍 验证监控端点...")
        
        monitoring_endpoints = [
            ("系统指标", "GET", f"{self.api_v1}/metrics"),
            ("Vision API指标", "GET", f"{self.api_v1}/vision-api-metrics"),
            ("缓存指标", "GET", f"{self.api_v1}/cache-metrics"),
            ("批处理指标", "GET", f"{self.api_v1}/batch-metrics"),
            ("性能指标", "GET", f"{self.api_v1}/performance-metrics"),
        ]
        
        for name, method, url in monitoring_endpoints:
            result = self.test_endpoint(name, method, url)
            
            if result['status'] == 'success':
                print(f"✅ {name}: 正常")
                self.results['working'].append(result)
            else:
                print(f"❌ {name}: 失败")
                self.results['broken'].append(result)
    
    def generate_report(self):
        """生成详细报告"""
        print("\n" + "="*60)
        print("📊 生产环境API验证报告")
        print("="*60)
        
        working_count = len(self.results['working'])
        broken_count = len(self.results['broken'])
        warning_count = len(self.results['warnings'])
        total_count = working_count + broken_count + warning_count
        
        print(f"📈 总体状态:")
        print(f"  ✅ 正常功能: {working_count}")
        print(f"  ❌ 故障功能: {broken_count}")
        print(f"  ⚠️ 警告功能: {warning_count}")
        print(f"  📊 总计: {total_count}")
        
        if total_count > 0:
            success_rate = (working_count / total_count) * 100
            print(f"  🎯 成功率: {success_rate:.1f}%")
        
        # 核心功能状态
        print(f"\n🔧 核心功能状态:")
        core_functions = ['根路径', '健康检查', '图片上传', '图片信息', '系统指标']
        core_working = [r for r in self.results['working'] if r['name'] in core_functions]
        core_broken = [r for r in self.results['broken'] if r['name'] in core_functions]
        
        if len(core_working) >= 4:  # 至少4个核心功能正常
            print("  ✅ 核心功能基本正常")
        else:
            print("  ❌ 核心功能存在问题")
        
        # 详细问题分析
        if broken_count > 0:
            print(f"\n❌ 故障功能详情:")
            for result in self.results['broken']:
                print(f"  - {result['name']}: 状态码 {result.get('status_code', 'N/A')}")
                if 'details' in result and 'error_message' in result['details']:
                    print(f"    错误: {result['details']['error_message']}")
        
        if warning_count > 0:
            print(f"\n⚠️ 警告功能详情:")
            for result in self.results['warnings']:
                print(f"  - {result['name']}: 状态码 {result.get('status_code', 'N/A')}")
                if 'details' in result and 'error_message' in result['details']:
                    print(f"    原因: {result['details']['error_message']}")
        
        # 建议
        print(f"\n💡 建议:")
        if broken_count == 0:
            print("  🎉 API运行状态良好!")
        else:
            print("  🔧 需要修复故障功能")
            
        if warning_count > 0:
            print("  ⚙️ 检查Vision API和其他外部服务配置")
        
        # 保存详细报告
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': total_count,
                'working': working_count,
                'broken': broken_count,
                'warnings': warning_count,
                'success_rate': (working_count / total_count * 100) if total_count > 0 else 0
            },
            'results': self.results
        }
        
        with open('production_verification_report.json', 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 详细报告已保存到: production_verification_report.json")
        
        return broken_count == 0
    
    def run_verification(self):
        """运行完整验证"""
        print("🚀 开始生产环境API验证")
        print(f"🌐 目标: {self.base_url}")
        print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # 基础端点验证
        self.verify_basic_endpoints()
        
        # 图片操作验证
        self.verify_image_operations()
        
        # 监控端点验证
        self.verify_monitoring_endpoints()
        
        # 生成报告
        return self.generate_report()

def main():
    """主函数"""
    verifier = ProductionAPIVerifier()
    success = verifier.run_verification()
    
    if success:
        print("\n🎉 生产环境API验证通过!")
        sys.exit(0)
    else:
        print("\n⚠️ 生产环境API存在一些问题，但核心功能可能正常")
        sys.exit(1)

if __name__ == "__main__":
    main()