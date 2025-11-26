import xml.etree.ElementTree as ET
import pandas as pd
import json
from io import StringIO

def initialize_data_container():
    """初始化数据容器"""
    data = {
        'session_id': [],
        'round_id': [],
        'intent_name': [],
        'second_intent_name': [],  # 新增的second_intent_name列
        'actual_answer': []
    }
    
    # 添加产品相关列，5个产品名称（含价格）和5个位置
    for i in range(1, 6):
        data[f'product_name{i}'] = []  # 这个列将包含名称和价格
        data[f'product_location{i}'] = []
    
    return data

def parse_json_block(block_text):
    """解析JSON数据块"""
    try:
        return json.loads(block_text.strip().replace('&quot;', '"'))
    except (json.JSONDecodeError, AttributeError):
        return None

def extract_fields_from_json(json_data):
    """从JSON数据中提取关键字段"""
    fields = {
        'session_id': json_data.get('session_id'),
        'round_id': json_data.get('round_id'),
        'intent_name': json_data.get('intent_name'),
        'second_intent_name': json_data.get('second_intent_name'),  # 新增的second_intent_name字段
        'answer': json_data.get('answer', ''),
        'parameters': json_data.get('parameters', [])
    }
    return fields

def extract_product_info(parameters):
    """从parameters中提取产品信息"""
    products = []
    standalone_locations = []  # 存储独立的location信息
    
    for param_group in parameters:
        if not isinstance(param_group, dict):
            continue
            
        product_list = param_group.get('list', [])
        if not isinstance(product_list, list):
            continue
            
        product_info = {
            'name_with_price': None,  # 合并名称和价格
            'location': None
        }
        
        name = None
        price = None
        has_product_info = False
        
        for param in product_list:
            if not isinstance(param, dict):
                continue
                
            param_name = param.get('param_name')
            param_value = param.get('param_value')
            
            if param_name == 'product_name':
                name = param_value
                has_product_info = True
            elif param_name == 'product_price':
                price = param_value
            elif param_name == 'product_location':
                product_info['location'] = param_value
            elif param_name == 'location':  # 独立的location参数
                standalone_locations.append(param_value)
        
        # 合并名称和价格
        if name and price:
            product_info['name_with_price'] = f"{name}（{price}）"
        elif name:
            product_info['name_with_price'] = name
        
        # 如果有产品信息，添加到产品列表
        if has_product_info:
            products.append(product_info)
    
    return products, standalone_locations

def process_http_sample(http_sample, data):
    """处理单个httpSample元素"""
    response_data = http_sample.find('responseData')
    if response_data is None or not response_data.text:
        return
    
    session_id = None
    round_id = None
    intent_name = None
    second_intent_name = None
    answer_parts = []
    all_products = []
    standalone_locations = []
    
    for block in StringIO(response_data.text):
        json_data = parse_json_block(block)
        if not json_data:
            continue
        
        fields = extract_fields_from_json(json_data)
        
        # 只取第一个有效值
        if session_id is None:
            session_id = fields['session_id']
        if round_id is None:
            round_id = fields['round_id']
        if intent_name is None:
            intent_name = fields['intent_name']
        if second_intent_name is None:
            second_intent_name = fields['second_intent_name']
        
        if fields['answer']:
            answer_parts.append(fields['answer'])
        
        # 提取产品信息和独立的location
        products, locations = extract_product_info(fields['parameters'])
        all_products.extend(products)
        standalone_locations.extend(locations)
    
    # 添加到数据容器
    if all([session_id, round_id, intent_name]):
        data['session_id'].append(session_id)
        data['round_id'].append(round_id)
        data['intent_name'].append(intent_name)
        data['second_intent_name'].append(second_intent_name)
        data['actual_answer'].append(''.join(answer_parts))
        
        # 添加产品信息到对应的列
        for i in range(1, 6):
            product_idx = i - 1
            if product_idx < len(all_products):
                product = all_products[product_idx]
                data[f'product_name{i}'].append(product['name_with_price'])
                # 优先使用产品自带的location，没有的话使用独立的location
                if product['location']:
                    data[f'product_location{i}'].append(product['location'])
                elif standalone_locations:
                    data[f'product_location{i}'].append(standalone_locations.pop(0))
                else:
                    data[f'product_location{i}'].append(None)
            else:
                # 如果没有足够的产品，填充空值
                data[f'product_name{i}'].append(None)
                if standalone_locations:
                    data[f'product_location{i}'].append(standalone_locations.pop(0))
                else:
                    data[f'product_location{i}'].append(None)

def save_to_csv(data, csv_file):
    """将数据保存为CSV文件"""
    df = pd.DataFrame(data)
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')

def xml_to_csv(xml_file, csv_file):
    """主转换函数"""
    data = initialize_data_container()
    
    # 解析XML
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # 处理每个httpSample
    for http_sample in root.findall('httpSample'):
        process_http_sample(http_sample, data)
    
    # 保存结果
    save_to_csv(data, csv_file)

def main():
    """主函数"""
    input_file = 'output1.xml'
    output_file = 'test.csv'
    xml_to_csv(input_file, output_file)
    print(f"转换完成，结果已保存到 {output_file}")

if __name__ == "__main__":
    main()
