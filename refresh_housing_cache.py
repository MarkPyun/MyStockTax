"""
주택재고량 캐시 삭제 및 새로고침
"""
import requests
import json

print("="*80)
print("주택재고량 캐시 새로고침")
print("="*80)

BASE_URL = "http://127.0.0.1:5000"
ENDPOINT = "/api/economy/housing-inventory/refresh"

print(f"\nURL: {BASE_URL}{ENDPOINT}")
print("-"*80)

try:
    print("\n🔄 새로고침 API 호출 중...")
    response = requests.post(f"{BASE_URL}{ENDPOINT}", json={}, timeout=60)
    
    print(f"응답 코드: {response.status_code}")
    print("-"*80)
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ 성공 응답:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if 'chart_data' in data:
            chart_data = data['chart_data']
            values = chart_data.get('inventory_values', [])
            labels = chart_data.get('labels', [])
            
            print("\n📊 새로고침된 데이터:")
            print("-"*80)
            
            # 2021Q1 ~ 2024Q2 확인
            for year in range(2021, 2025):
                for q in range(1, 5):
                    label = f"{year}Q{q}"
                    if label in labels:
                        idx = labels.index(label)
                        value = values[idx]
                        status = "✅" if value is not None else "❌"
                        val_str = f"{value:.2f}" if value is not None else "None"
                        print(f"  {label}: {val_str:>10} {status}")
                    if year == 2024 and q == 2:
                        break
            
            none_count = sum(1 for v in values if v is None)
            valid_count = len(values) - none_count
            
            print(f"\n통계:")
            print(f"  정상 값: {valid_count}개")
            print(f"  None 값: {none_count}개")
    else:
        print(f"\n❌ 오류 응답 ({response.status_code}):")
        print(response.text)
        
except Exception as e:
    print(f"\n❌ 오류: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)

