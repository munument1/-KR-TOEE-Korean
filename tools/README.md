# TOEE 한국어 통합 패치 도구

최종 번역 시트의 `Korean` 열을 원본 TOEE / Circle of Eight / TemplePlus 텍스트 파일에 안전하게 재주입하는 도구입니다.

## 권장: GUI 통합 설치기

`toee_korean_installer_gui.pyw`는 사용자가 경로를 직접 지정하는 Windows GUI입니다.

직접 지정 항목:

- **TOEE 설치 폴더** — `data`, `modules/ToEE`가 들어 있는 게임 루트
- **TemplePlus tpdata 폴더** — 예: `%LOCALAPPDATA%\TemplePlus\app-1.0.xx\tpdata`
- **최종 번역 XLSX** — `TOEE_Translation_FILTERED_v2.xlsx`
- **패치 출력 폴더** — 패치 파일만 생성할 때 사용

TemplePlus는 `자동 찾기` 버튼도 지원하지만 직접 경로 입력/찾아보기가 기본입니다.

### 실행 방식

1. **사전 검사**
   - TOEE / Co8 / TemplePlus 전체 원문과 XLSX를 대조합니다.
   - 원문 불일치, 누락, CTRL 복원 오류가 있으면 설치하지 않습니다.
2. **통합 설치 (권장)**
   - 먼저 전체 패치를 임시 폴더에 생성해 검증합니다.
   - 전체 검증 성공 후에만 TOEE / Co8 / TemplePlus를 동시에 적용합니다.
   - `TOEE_Korean_Backup_YYYYMMDD_HHMMSS`에 기존 파일을 먼저 백업합니다.
   - 설치 도중 오류가 나면 현재 설치 작업을 자동 롤백합니다.
3. **패치 파일만 생성**
   - 원본은 수정하지 않고 별도 오버레이 폴더만 생성합니다.

경로 설정은 `%APPDATA%\TOEE_Korean_Installer\settings.json`에 저장되어 다음 실행 때 다시 불러옵니다.

## Windows EXE

GitHub Actions의 **Build Windows Installer** 워크플로가 아래 파일을 단일 실행 파일로 빌드합니다.

`TOEE_Korean_Installer.exe`

EXE에는 Python 실행 환경과 `openpyxl`, 재주입 코어가 함께 묶이므로 최종 사용자는 Python을 별도로 설치할 필요가 없습니다. 최종 번역 XLSX와 게임/TemplePlus 경로만 지정하면 됩니다.

## 구성 파일

- `toee_korean_installer_gui.pyw` — GUI 통합 설치기
- `toee_apply_korean_translation.py` — DLG/MES/TAB/JSON 재주입 및 검증 코어
- `TOEE_한글패치_생성.bat` — 기존 개발/수동 패치 생성용 래퍼

최종 번역 XLSX는 저장소에 포함하지 않습니다. 게임 원문이 대량 포함된 작업용 데이터이므로 별도 관리합니다.

## 재주입 원칙

시트에서 게임 파일을 새로 조립하지 않습니다. **현재 설치된 원본 파일을 읽고 번역 대상 필드만 교체**합니다.

- DLG: A/B 텍스트만 교체. Selector, Condition, NextID, Effect 및 기능행 유지
- MES: ID 유지, 표시 문자열만 교체, 주석/빈 줄 유지
- TAB/TSV: `EntryID + COLn` 위치만 교체
- JSON: 시트의 JSON path가 가리키는 문자열만 교체
- `⟦CTRL:NN⟧`은 실제 C0 제어문자로 복원
- 시트 English와 설치본 원문이 다르면 기본적으로 적용 보류
- 출력은 UTF-8 무BOM

## 검증 이력

실제 `00002black jay.dlg`와 `bonus.mes`를 이용한 470행 샘플에서 470/470 적용을 확인했습니다.

- DLG ID/Selector/Condition/NextID/Effect 구조 동일
- DLG `K:`/`E:` 기능행 유지
- MES ID 순서/주석 유지
- C0 제어문자 복원 합성 테스트 통과
- TAB `COLn` 패치 합성 테스트 통과
- JSON path 패치 합성 테스트 통과
- GUI 통합 설치 트랜잭션 합성 테스트 통과(백업 → 적용 → 롤백 경로)
