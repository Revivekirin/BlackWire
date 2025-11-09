import pandas as pd
from datetime import datetime
import os

# --- 설정 ---
base_path = "/Users/kimjihe/Desktop/git/2025capstone/extract/"
today_str = datetime.now().strftime("%Y%m%d")

file_a_path = os.path.join(base_path, f"urls_with_groups_ip_{today_str}.csv")
file_b_path = os.path.join(base_path, "leak_data_train.csv")
output_file_path = os.path.join(base_path, "leak_data_test.csv")

# --- CSV 로딩 ---
print(f"A 파일 로딩 시도: {file_a_path}")
try:
    df_a = pd.read_csv(file_a_path)
    # --- 컬럼명 일치 작업 ---
    # 이전 스크립트에서 생성된 파일(file_a)의 컬럼명을 이 스크립트에서 사용할 이름으로 변경
    # file_a의 실제 컬럼명: "html_file", "group", "extracted_url", "domain", "ip_address"
    # 이 스크립트에서 기대하는/사용할 이름: 'url' (필수), 'html_file', 'group' (선택적이지만 최종 파일에 포함 원함)
    
    rename_map_a = {}
    # URL 컬럼명 변경 (필수)
    if 'extracted_url' in df_a.columns:
        rename_map_a['extracted_url'] = 'url'
    elif 'url' not in df_a.columns: # extracted_url도 없고 url도 없으면 문제가 있음
        print(f"경고: '{file_a_path}'에 'extracted_url' 또는 'url' 컬럼이 없습니다. 'url' 컬럼을 기준으로 작업합니다.")

    # HTML 파일명 컬럼 변경 (최종 파일에 'html_file'로 저장하고 싶다면)
    if 'html_file' in df_a.columns:
        rename_map_a['html_file'] = 'html_file' # 최종 파일에 원하는 컬럼명
    
    # 그룹명 컬럼 변경 (최종 파일에 'group'으로 저장하고 싶다면)
    if 'group' in df_a.columns:
        rename_map_a['group'] = 'group' # 최종 파일에 원하는 컬럼명

    if rename_map_a:
        df_a.rename(columns=rename_map_a, inplace=True)
        print(f"'{file_a_path}'의 컬럼명이 조정되었습니다. (변경된 매핑: {rename_map_a})")

except FileNotFoundError:
    print(f"오류: 파일 '{file_a_path}'을(를) 찾을 수 없습니다. 스크립트를 종료합니다.")
    exit()
except Exception as e:
    print(f"오류: 파일 '{file_a_path}' 로딩 중 문제 발생: {e}")
    exit()

print(f"B 파일 로딩 시도: {file_b_path}")
try:
    df_b = pd.read_csv(file_b_path)
    # df_b도 'url' 컬럼이 필요. 만약 다른 이름이라면 df_b에 대해서도 rename 필요.
    # 여기서는 df_b에 'url' 컬럼이 있다고 가정.
except FileNotFoundError:
    print(f"오류: 파일 '{file_b_path}'을(를) 찾을 수 없습니다. 스크립트를 종료합니다.")
    exit()
except Exception as e:
    print(f"오류: 파일 '{file_b_path}' 로딩 중 문제 발생: {e}")
    exit()

# 'url' 열 존재 여부 확인 (컬럼명 변경 후)
if 'url' not in df_a.columns:
    print(f"오류: '{file_a_path}' 파일 (컬럼명 조정 후)에 'url' 열이 없습니다.")
    exit()
if 'url' not in df_b.columns:
    print(f"오류: '{file_b_path}' 파일에 'url' 열이 없습니다.")
    exit()

# --- 1단계: df_a에서 df_b의 URL을 가진 행 제거 ---
# df_a_filtered는 df_a의 모든 컬럼(조정된 이름 포함)을 가짐
df_a_filtered = df_a[~df_a['url'].isin(df_b['url'])].copy()
print(f"'{file_a_path}'에서 '{file_b_path}'와 중복된 URL 제거 후 남은 행: {len(df_a_filtered)}")

if df_a_filtered.empty:
    print(f"'{file_a_path}'의 모든 URL이 '{file_b_path}'에 포함되어 있어 추가할 새 데이터가 없습니다.")
    # 이 경우, 기존 output_file_path 내용이 유지될 수 있도록 처리합니다.
    # 만약 output_file_path가 없다면 빈 파일이 생성될 것입니다.
    # df_final_output을 빈 DataFrame으로 시작할 수 있습니다.
    # df_final_output = pd.DataFrame() # 이렇게 하면 아래 로직에서 기존 파일만 로드 시도


# --- 2단계: 기존 output_file_path 파일 로드 및 병합 ---
df_final_output_list = []

if os.path.exists(output_file_path):
    print(f"기존 '{output_file_path}' 파일 로딩 시도...")
    try:
        df_existing_test = pd.read_csv(output_file_path)
        if 'url' not in df_existing_test.columns: # 기존 파일에도 url 컬럼은 필수
            print(f"경고: 기존 '{output_file_path}' 파일에 'url' 열이 없습니다. 새 데이터로만 구성합니다.")
            if not df_a_filtered.empty:
                 df_final_output_list.append(df_a_filtered)
        elif df_existing_test.empty:
            print(f"기존 '{output_file_path}' 파일이 비어있습니다.")
            if not df_a_filtered.empty:
                 df_final_output_list.append(df_a_filtered)
        else:
            print(f"기존 '{output_file_path}' 파일 로드 완료 (행: {len(df_existing_test)}).")
            df_final_output_list.append(df_existing_test)
            if not df_a_filtered.empty:
                df_final_output_list.append(df_a_filtered)
            
    except pd.errors.EmptyDataError:
        print(f"경고: 기존 '{output_file_path}' 파일이 비어있지만 유효한 CSV가 아닙니다. 새 데이터로만 구성합니다.")
        if not df_a_filtered.empty:
            df_final_output_list.append(df_a_filtered)
    except Exception as e:
        print(f"경고: 기존 '{output_file_path}' 파일 로드 중 오류 발생: {e}. 새 데이터로만 구성합니다.")
        if not df_a_filtered.empty:
            df_final_output_list.append(df_a_filtered)
else:
    print(f"'{output_file_path}' 파일이 존재하지 않습니다. 새로 생성합니다.")
    if not df_a_filtered.empty:
        df_final_output_list.append(df_a_filtered)

# --- 3단계: 데이터 병합 및 최종 중복 제거 ---
if df_final_output_list:
    df_final_output = pd.concat(df_final_output_list, ignore_index=True)
    print(f"병합 후 총 행 수 (중복 제거 전): {len(df_final_output)}")
    
    # 중복된 URL이 있다면, 병합 시 먼저 온 행(기존 test.csv의 행)을 유지
    # concat 순서상 df_existing_test가 먼저 오므로 keep='first'가 적절
    df_final_output.drop_duplicates(subset=['url'], keep='first', inplace=True)
    print(f"최종 중복 제거 후 남은 행: {len(df_final_output)}")
else:
    df_final_output = pd.DataFrame() # 처리할 데이터가 없는 경우 빈 DataFrame
    print("병합 및 필터링 후 최종 데이터가 비어있습니다.")

# --- 4단계: 결과 저장 ---
# df_final_output 에 html_file, group 등의 컬럼이 포함되어 저장됩니다.
# (df_a_filtered 에서 유래했거나, df_existing_test 에 이미 있었다면)
try:
    # 저장 전에 최종 컬럼 확인 (디버깅용)
    if not df_final_output.empty:
        print(f"최종 저장될 파일의 컬럼: {df_final_output.columns.tolist()}")
    else:
        print("저장할 데이터가 없습니다. 빈 파일이 생성될 수 있습니다.")
        # 빈 DataFrame도 to_csv로 저장하면 헤더만 있는 파일이 생성됨 (index=False 시 헤더 없음)
        # 만약 빈 파일 생성을 원치 않으면 여기서 분기 처리 가능

    df_final_output.to_csv(output_file_path, index=False, encoding='utf-8-sig')
    print(f"최종 결과 저장 완료: {output_file_path} (총 행: {len(df_final_output)})")
except Exception as e:
    print(f"오류: 최종 파일 '{output_file_path}' 저장 중 문제 발생: {e}")
