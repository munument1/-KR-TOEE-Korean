# TOEE 한국어 패치 재주입 도구

최종 번역 시트의 `Korean` 열을 원본 TOEE / Circle of Eight / Temple+ 텍스트 파일에 안전하게 재주입하는 도구입니다.

## 파일

- `toee_apply_korean_translation.py` — DLG/MES/TAB/JSON 번역 재주입 및 검증
- `TOEE_한글패치_생성.bat` — 게임 루트에서 실행하는 Windows 원클릭 래퍼

최종 번역 XLSX는 저장소에 포함하지 않습니다. 게임 원문이 대량 포함된 작업용 데이터이므로 별도 관리합니다.

## 원칙

시트에서 게임 파일을 새로 조립하지 않습니다. **현재 설치된 원본 파일을 읽고 번역 대상 필드만 교체**합니다.

- DLG: A/B 텍스트만 교체. Selector, Condition, NextID, Effect 및 기능행 유지
- MES: ID 유지, 표시 문자열만 교체, 주석/빈 줄 유지
- TAB/TSV: `EntryID + COLn` 위치만 교체
- JSON: 시트의 JSON path가 가리키는 문자열만 교체
- `⟦CTRL:NN⟧`은 실제 C0 제어문자로 복원
- 시트 English와 설치본 원문이 다르면 기본적으로 적용을 보류
- 출력은 UTF-8 무BOM

## 사용

`TOEE_Translation_FILTERED_v2.xlsx`와 두 도구 파일을 TOEE 게임 루트에 둔 뒤 `TOEE_한글패치_생성.bat`을 실행합니다.

기본 출력은 `TOEE_Korean_Patch_Output`이며 원본 파일을 직접 수정하지 않습니다. Temple+는 `%LOCALAPPDATA%\TemplePlus\app-*\tpdata`의 최신 설치를 자동 감지합니다.

성공 시 `PATCH_REPORT.json`에서 다음을 확인합니다.

- `rows_applied == translation_rows`
- `source_mismatches == 0`
- `missing_entries_or_files == 0`
- `file_errors == 0`
- `control_marker_files_remaining == []`

## 검증 이력

실제 `00002black jay.dlg`와 `bonus.mes`를 이용한 470행 샘플에서 470/470 적용을 확인했습니다.

- DLG ID/Selector/Condition/NextID/Effect 구조 동일
- DLG `K:`/`E:` 기능행 유지
- MES ID 순서/주석 유지
- C0 제어문자 복원 합성 테스트 통과
- TAB `COLn` 패치 합성 테스트 통과
- JSON path 패치 합성 테스트 통과
