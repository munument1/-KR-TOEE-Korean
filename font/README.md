# Temple+ 한국어 폰트 적용 작업물

이 폴더에는 Temple+ 환경에서 TOEE 한국어 텍스트를 표시하기 위한 폰트 설정이 들어 있습니다.

## 현재 구성

### 1. 레거시 UI / 대화 / 인터페이스 MES

`tpdata/fonts/mapping.json`의 원본 배열 구조와 각 ID의 크기/굵기/줄높이 값을 유지하면서, Temple+가 사용하는 6개 레거시 폰트 ID를 한글 지원 폰트로 매핑했습니다.

```text
arial-10       -> NanumBarunGothic
arial-12       -> NanumBarunGothic
arial-bold-10  -> NanumBarunGothic
arial-bold-24  -> NanumBarunGothic
priory-12      -> NanumBarunGothic
scurlock-48    -> 우아한 세리프
```

`art/interface/**.mes` 파일에서 `priory-12`, `arial-10`, `arial-bold-24` 같은 기존 폰트 ID를 직접 참조하더라도, Temple+의 폰트 매핑을 통해 위 한글 폰트가 사용됩니다. 따라서 폰트 적용만을 위해 interface MES의 폰트 ID를 개별 수정할 필요는 없습니다.

실게임 Hommlet의 Kent 대화에서 다음 항목을 확인했습니다.

- NPC 한국어 대사 정상 표시
- 플레이어 한국어 선택지 정상 표시
- UTF-8 DLG 한국어 출력 정상

> `mapping.json`은 객체 하나가 아니라 `id` 항목들이 들어 있는 JSON 배열 형식이어야 합니다. 구조를 다른 형태로 바꾸면 Temple+ 시작/로드 과정에서 문제가 생길 수 있습니다.

### 2. Temple+ 신형 공통 UI

`tpdata/templeplus/text_styles.json`을 추가하여 Temple+ 신형 UI의 공통 텍스트 스타일을 `NanumBarunGothic`으로 지정했습니다.

대상 스타일:

```text
default
arial-10-title-text
default-button-text
chargen-button-text
priory-title
```

`button_styles.json`은 위 text style ID를 참조하므로 폰트 적용을 위해 별도로 수정하지 않습니다.

### 3. 메인 메뉴

`tpdata/templeplus/ui/main_menu.json`은 Temple+의 현대식 UI/DirectWrite 경로에서 다음 값을 사용합니다.

```text
fontFamily: 우아한 세리프
pointSize: 30
버튼 세로 간격: 44px
```

한국어 메인 메뉴 출력과 레이아웃은 실제 게임에서 정상 표시되는 것을 확인했습니다.

추가로 아래 메뉴 JSON의 직접 폰트 지정도 `NanumBarunGothic`으로 변경했습니다.

```text
main_menu_cinematics.json
main_menu_setpieces.json
```

## 필요한 폰트

현재 설정은 아래 폰트가 Temple+의 `tpdata/fonts/` 폴더에 존재한다는 전제로 작성되어 있습니다.

```text
NanumBarunGothic.ttf
NanumBarunGothicBold.ttf
GraceSerif-Regular.ttf
GraceSerif-Bold.ttf
```

GraceSerif의 DirectWrite 패밀리 이름은 다음과 같습니다.

```text
우아한 세리프
```

현재 이 저장소의 `font/tpdata/fonts/`에는 폰트 바이너리 자체가 포함되어 있지 않습니다.

업로드할 원본 파일의 SHA-256 확인값:

```text
NanumBarunGothic.ttf      9b872773134e2e4d8c0b17021266786576db06c843ede0d0b523b214a450756c
NanumBarunGothicBold.ttf  39bba4cd9bd2986143825c8654abbb62443914ab33b346c0c929a916f5d98bf2
GraceSerif-Regular.ttf    33eb8227c4ecd0cfa4e4ec18d9f448a9530dfc36bb8034bf3b409b572aba64d1
GraceSerif-Bold.ttf       bbdc46f95144d4705c03b2b93da43464adc71ad8c3519702c7e0f04ae8b75d25
```

## 폰트 라이선스

폰트 바이너리를 번들할 때 필요한 라이선스 고지 파일을 같은 폴더에 포함합니다.

```text
LICENSE-NanumBarunGothic.txt
LICENSE-GraceSerif.txt
```

- NanumBarunGothic: NAVER, SIL Open Font License 1.1
- GraceSerif / 우아한세리프: Pear Type Foundry, SIL Open Font License 1.1

두 폰트 모두 원본 글꼴 파일 자체를 별도로 유료 판매하는 것은 허용되지 않으며, 이 패치처럼 소프트웨어와 함께 번들·재배포할 때는 각 라이선스 고지를 유지해야 합니다.

## 적용 방법

1. Temple+를 완전히 종료합니다.
2. 현재 사용하는 Temple+ 설치 폴더의 기존 설정을 백업합니다.
3. 이 폴더의 `tpdata/` 내용을 Temple+의 `tpdata/`에 같은 상대 경로로 덮어씁니다.
4. 필요한 폰트가 `tpdata/fonts/`에 존재하는지 확인합니다.
5. Temple+를 다시 실행합니다.

대표적인 Temple+ 설치 경로:

```text
%LOCALAPPDATA%\TemplePlus\app-*\
```

Temple+ 업데이트에 따라 `app-*` 버전 폴더명은 달라질 수 있습니다.

## 현재 텍스트 인코딩 방향

현재까지의 실게임 테스트에서는 번역 리소스를 **UTF-8 무BOM**으로 저장한 구성이 정상 동작했습니다.

메인 메뉴와 대화창은 이미 실게임에서 확인했으며, 캐릭터 생성·인벤토리·아이템 설명·도움말·전투 로그 등은 통합 번역 반영 후 추가 QA가 필요합니다.

## 주의

이 폴더는 한국어화 개발/WIP 설정입니다. Temple+ 업데이트 또는 사용자의 별도 폰트/UI 설정과 충돌할 수 있으므로 기존 파일을 백업해 두는 것을 권장합니다.
