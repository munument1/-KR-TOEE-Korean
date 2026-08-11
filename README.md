# Temple of Elemental Evil 한국어화

**The Temple of Elemental Evil (TOEE) 한국어화 프로젝트**입니다.

게임의 텍스트, 한글 폰트 표시, 로딩/엔딩 슬라이드 등 한국어 플레이에 필요한 리소스를 단계적으로 정리하고 있습니다.

> 첫 통합 배포판은 GitHub Releases에서 받을 수 있습니다. 추가 실게임 회귀 테스트와 문구 다듬기는 계속 진행합니다.

## 통합 패치 설치

1. GitHub Releases에서 최신 ZIP을 내려받아 압축을 풉니다.
2. 게임과 TemplePlus를 모두 종료합니다.
3. `GAME_FOLDER` 안의 내용물을 Temple of Elemental Evil 게임 폴더에 복사합니다.
4. `TEMPLEPLUS_FOLDER` 안의 내용물을 TemplePlus `app-1.0.98` 폴더에 복사합니다.
5. 같은 이름의 파일은 모두 덮어쓴 뒤 TemplePlus를 실행합니다.

통합 패치에는 게임/Co8/TemplePlus 번역, 한글 폰트 호환 파일, 인터페이스 이미지 3개, 한글 슬라이드 116장이 포함됩니다.

## 현재 구성

### `font/`
Temple+ 환경에서 한국어를 표시하기 위한 실게임 검증 폰트/UI 설정입니다.

현재 확인된 구성:

- NPC 대화창/플레이어 선택지: `priory-12 -> NanumBarunGothic`
- 메인 메뉴: `우아한 세리프` 30pt
- 메인 메뉴 버튼 세로 간격: 44px
- 현재 테스트 번역 리소스: UTF-8 무BOM
- Temple+ DirectWrite 경로에서 한국어 출력 확인
- NanumBarunGothic / GraceSerif TTF 4개 및 OFL 라이선스 번들

자세한 적용 방법은 [`font/README.md`](font/README.md)를 참고하세요.

### `slide/`
로딩/엔딩/지역 설명/이벤트 슬라이드 이미지 한국어화 작업 영역입니다.

- 대상: 116장
- 해상도: 800×500
- 형식: JPEG
- 원본 파일명 유지
- 정확한 대상 파일 목록은 [`slide/FILELIST.txt`](slide/FILELIST.txt) 참고

슬라이드 116장은 통합 배포 ZIP에 포함되어 있습니다.

### `tools/`
최종 번역 시트를 실제 TOEE / Co8 / TemplePlus 원본 텍스트 파일에 안전하게 재주입하기 위한 도구입니다.

현재는 **사용자가 각 설치 경로를 직접 지정하는 Windows GUI 통합 설치기**를 기본 방향으로 사용합니다.

- `toee_korean_installer_gui.pyw`: TOEE / TemplePlus / XLSX 경로 직접 지정 GUI
- `toee_apply_korean_translation.py`: DLG / MES / TAB / JSON 번역 재주입 코어
- `toee_font_bundle_hook.py`: 폰트 4개 SHA-256 검증 및 TemplePlus 폰트/UI 설정 통합
- GitHub Actions: `TOEE_Korean_Installer.exe` 단일 실행 파일 자동 빌드
- 전체 사전검사 통과 후에만 TOEE / Co8 + TemplePlus 동시 설치
- 설치 전 날짜별 원본 백업 생성
- 설치 도중 오류 발생 시 현재 작업 자동 롤백
- 원본 파일 전체를 재구성하지 않고 번역 대상 필드만 교체
- `⟦CTRL:NN⟧` 제어문자를 런타임 문자로 복원
- 시트 English와 설치본 원문이 다르면 자동 보류
- 번들된 TTF 4개의 SHA-256이 기준값과 다르면 설치기 빌드/설치를 중단

자세한 내용은 [`tools/README.md`](tools/README.md)를 참고하세요.

## 번역 / QA 상태

최종 번역 시트 기준 **70,457개 원문 행의 Korean 공란이 0**이며 최종 구조 QA를 통과했습니다.

검증 항목:

- CTRL / TAG / CMD / `@t` 불일치 0
- 중괄호 구조 불일치 0
- RowID 중복 0
- 누락 청크 0 (312/312)
- 사용자 표시 도움말 영어 원문 잔존 0
- `B:` 기능 접두사 누락 0
- `tokens truncated` 0
- `rod` 용어 회귀검사 통과 (`rod = 막대`, `wand = 완드`, `staff`는 문맥 기준)

재주입 도구는 실제 `00002black jay.dlg` + `bonus.mes` 샘플 470행에서 **470/470 적용**을 확인했고, DLG 기능 구조와 MES ID/주석 보존을 재검증했습니다.

## 작업 상태

- [x] Temple+ 대화창 한글 폰트 매핑 교정 및 실게임 확인
- [x] 메인 메뉴 한글 DirectWrite 출력 및 GraceSerif 레이아웃 확인
- [x] 한글 TTF 4개 및 OFL 라이선스 저장소 탑재
- [x] UTF-8 무BOM DLG 한국어 대화 출력 확인
- [x] 전체 게임 텍스트 번역 완료
- [x] 전체 텍스트 구조/의미 델타 QA 및 FINAL GATE
- [x] DLG/MES/TAB/JSON 재주입 도구 작성 및 샘플 검증
- [x] TOEE / Co8 + TemplePlus 경로 지정 GUI 통합 설치기 작성
- [x] Windows 단일 EXE 자동 빌드 워크플로 구성
- [ ] `[exit]`, `[Barter]` 등 대괄호 UI/행동문구 최종 정규화
- [x] 슬라이드 이미지 116장 통합 배포
- [ ] 슬라이드 영문 잔상/글자 잘림 최종 QA
- [ ] 대화 외 UI·로그·도움말·아이템/주문/특기 등 전 영역 폰트 QA
- [x] 게임/Co8/TemplePlus 한국어 리소스 통합 생성
- [x] 한글 호환 패치 및 이미지 포함 최종 ZIP 구성
- [ ] 전체 구간 실게임 회귀 테스트

## 폰트 파일

저장소의 `font/tpdata/fonts/`에 아래 TTF 4개와 각 OFL 라이선스를 포함합니다.

- `NanumBarunGothic.ttf`
- `NanumBarunGothicBold.ttf`
- `GraceSerif-Regular.ttf`
- `GraceSerif-Bold.ttf`

GitHub Actions와 통합 설치기는 `font/README.md`에 기록된 SHA-256 기준값으로 파일 무결성을 검증합니다.

## 주의

이 저장소는 비공식 팬 한국어화 프로젝트입니다.
원작 게임 및 관련 상표의 권리는 각 권리자에게 있습니다.

게임 원본 실행 파일, DLL, DAT 등 상용 게임 바이너리는 이 저장소에 포함하지 않습니다.

## Credits

Korean localization project by **munument1**.
