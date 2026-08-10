# Temple+ 한국어 폰트 적용 작업물

이 폴더에는 Temple+ 환경에서 TOEE 한국어 텍스트를 표시하기 위해 실제 게임에서 검증한 폰트 설정이 들어 있습니다.

## 현재 검증된 구성

### 1. NPC 대화창 / 플레이어 선택지

`tpdata/fonts/mapping.json`의 원본 **배열 구조를 그대로 유지**하면서 `priory-12` 항목의 `fontFace`만 변경했습니다.

```text
Junicode -> NanumBarunGothic
```

`size`, `bold`, `italic`, `uniformLineHeight` 및 다른 폰트 항목은 기준 매핑 값을 유지합니다.

실게임 Hommlet의 Kent 대화에서 다음 항목을 확인했습니다.

- NPC 한국어 대사 정상 표시
- 플레이어 한국어 선택지 정상 표시
- UTF-8 DLG 한국어 출력 정상

> `mapping.json`은 객체 하나가 아니라 `id` 항목들이 들어 있는 JSON 배열 형식이어야 합니다. 구조를 다른 형태로 바꾸면 Temple+ 시작/로드 과정에서 문제가 생길 수 있습니다.

### 2. 메인 메뉴

`tpdata/templeplus/ui/main_menu.json`에서 Temple+의 현대식 UI/DirectWrite 경로를 사용하도록 메인 메뉴 표시 폰트를 지정했습니다.

현재 확정값:

```text
fontFamily: 우아한 세리프
pointSize: 30
버튼 세로 간격: 44px
```

한국어 메인 메뉴 출력과 레이아웃이 실제 게임에서 정상 표시되는 것을 확인했습니다.

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

이 저장소에는 현재 폰트 바이너리 자체를 포함하지 않습니다.

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

메인 메뉴와 대화창은 렌더링 경로가 다르므로, 향후 다른 UI·로그·도움말·아이템 설명 등도 통합 번역 완료 후 별도 QA를 진행할 예정입니다.

## 주의

이 폴더는 한국어화 개발/WIP 설정입니다. Temple+ 업데이트 또는 사용자의 별도 폰트/UI 설정과 충돌할 수 있으므로 기존 파일을 백업해 두는 것을 권장합니다.
