# Temple of Elemental Evil 한국어화

**The Temple of Elemental Evil (TOEE) 한국어화 프로젝트**입니다.

게임의 텍스트, 한글 폰트 표시, 로딩/엔딩 슬라이드 등 한국어 플레이에 필요한 리소스를 단계적으로 정리하고 있습니다.

> 현재 작업 중인 개발/WIP 저장소입니다. 완성 배포판이 아니며 파일 구성과 적용 방법은 작업 진행에 따라 변경될 수 있습니다.

## 현재 구성

### `font/`
Temple+ 환경에서 한국어를 표시하기 위한 실게임 검증 폰트/UI 설정입니다.

현재 확인된 구성:

- NPC 대화창/플레이어 선택지: `priory-12 -> NanumBarunGothic`
- 메인 메뉴: `우아한 세리프` 30pt
- 메인 메뉴 버튼 세로 간격: 44px
- 현재 테스트 번역 리소스: UTF-8 무BOM
- Temple+ DirectWrite 경로에서 한국어 출력 확인

자세한 적용 방법은 [`font/README.md`](font/README.md)를 참고하세요.

### `slide/`
로딩/엔딩/지역 설명/이벤트 슬라이드 이미지 한국어화 작업 영역입니다.

- 대상: 116장
- 해상도: 800×500
- 형식: JPEG
- 원본 파일명 유지
- 정확한 대상 파일 목록은 [`slide/FILELIST.txt`](slide/FILELIST.txt) 참고

슬라이드 이미지는 별도 작업 흐름에서 순차적으로 업로드/QA 중입니다.

### `tools/`
최종 번역 시트를 실제 TOEE / Co8 / TemplePlus 원본 텍스트 파일에 안전하게 재주입하기 위한 도구입니다.

현재는 **사용자가 각 설치 경로를 직접 지정하는 Windows GUI 통합 설치기**를 기본 방향으로 사용합니다.

- `toee_korean_installer_gui.pyw`: TOEE / TemplePlus / XLSX 경로 직접 지정 GUI
- `toee_apply_korean_translation.py`: DLG / MES / TAB / JSON 번역 재주입 코어
- GitHub Actions: `TOEE_Korean_Installer.exe` 단일 실행 파일 자동 빌드
- 전체 사전검사 통과 후에만 TOEE / Co8 + TemplePlus 동시 설치
- 설치 전 날짜별 원본 백업 생성
- 설치 도중 오류 발생 시 현재 작업 자동 롤백
- 원본 파일 전체를 재구성하지 않고 번역 대상 필드만 교체
- `⟦CTRL:NN⟧` 제어문자를 런타임 문자로 복원
- 시트 English와 설치본 원문이 다르면 자동 보류

자세한 내용은 [`tools/README.md`](tools/README.md)를 참고하세요.

## 번역 / QA 상태

최종 번역 시트 기준 **58,370개 원문 행의 Korean 공란이 0**이며 최종 구조 QA를 통과했습니다.

검증 항목:

- CTRL / TAG / CMD / `@t` 불일치 0
- 중괄호 구조 불일치 0
- RowID 중복 0
- `tokens truncated` 0
- `rod` 용어 회귀검사 통과 (`rod = 막대`, `wand = 완드`, `staff`는 문맥 기준)

재주입 도구는 실제 `00002black jay.dlg` + `bonus.mes` 샘플 470행에서 **470/470 적용**을 확인했고, DLG 기능 구조와 MES ID/주석 보존을 재검증했습니다.

## 작업 상태

- [x] Temple+ 대화창 한글 폰트 매핑 교정 및 실게임 확인
- [x] 메인 메뉴 한글 DirectWrite 출력 및 GraceSerif 레이아웃 확인
- [x] UTF-8 무BOM DLG 한국어 대화 출력 확인
- [x] 전체 게임 텍스트 번역 완료
- [x] 전체 텍스트 구조/의미 델타 QA 및 FINAL GATE
- [x] DLG/MES/TAB/JSON 재주입 도구 작성 및 샘플 검증
- [x] TOEE / Co8 + TemplePlus 경로 지정 GUI 통합 설치기 작성
- [x] Windows 단일 EXE 자동 빌드 워크플로 구성
- [ ] `[exit]`, `[Barter]` 등 대괄호 UI/행동문구 최종 정규화
- [ ] 슬라이드 이미지 116장 업로드
- [ ] 슬라이드 영문 잔상/글자 잘림 최종 QA
- [ ] 대화 외 UI·로그·도움말·아이템/주문/특기 등 전 영역 폰트 QA
- [ ] 전체 405개 대상 파일 한국어 리소스 통합 생성 및 실게임 회귀 테스트
- [ ] 최종 설치/배포 패키지 구성

## 폰트 파일

현재 저장소에는 폰트 바이너리 자체를 포함하지 않습니다. `font/README.md`에 적힌 폰트를 사용자가 별도로 준비해 Temple+의 `tpdata/fonts/`에 배치하는 방식으로 작업 중입니다.

## 주의

이 저장소는 비공식 팬 한국어화 프로젝트입니다.
원작 게임 및 관련 상표의 권리는 각 권리자에게 있습니다.

게임 원본 실행 파일, DLL, DAT 등 상용 게임 바이너리는 이 저장소에 포함하지 않습니다.

## Credits

Korean localization project by **munument1**.
