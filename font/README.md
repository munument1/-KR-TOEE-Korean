# Temple+ 한국어 대화창 폰트 매핑

이 폴더에는 Temple+ 환경에서 TOEE 한국어 대화문 표시를 시험하기 위한 폰트 매핑 교정본이 들어 있습니다.

## 변경 내용

`tpdata/fonts/mapping.json`의 기존 배열 구조를 유지하면서 `priory-12` 항목의 `fontFace`만 변경했습니다.

```text
Junicode -> NanumBarunGothic
```

`size`, `bold`, `italic`, `uniformLineHeight` 및 다른 폰트 항목은 기준 매핑 값 그대로 유지했습니다.

## 필요한 폰트

현재 매핑은 다음 폰트 파일이 Temple+의 `tpdata/fonts/` 폴더에 이미 존재한다는 전제로 작성되어 있습니다.

```text
NanumBarunGothic.ttf
NanumBarunGothicBold.ttf
```

이 저장소에는 현재 폰트 파일 자체를 포함하지 않습니다.

## 적용 방법

1. Temple+를 완전히 종료합니다.
2. 현재 사용하는 Temple+ 설치 폴더의 `tpdata/fonts/mapping.json`을 백업합니다.
3. 이 폴더의 `tpdata/fonts/mapping.json`을 같은 상대 경로에 덮어씁니다.
4. 위의 NanumBarunGothic 폰트 파일이 `tpdata/fonts/`에 존재하는지 확인합니다.
5. Temple+를 다시 실행하고 대화창의 자기소개 문구와 선택지를 확인합니다.

Temple+는 업데이트에 따라 `%LOCALAPPDATA%\TemplePlus\app-*\` 폴더명이 달라질 수 있으므로 특정 버전 번호를 고정하지 않습니다.

## 판정

- 한글 대화문이 정상 표시되면 폰트 매핑 경로가 정상 동작하는 것입니다.
- 글자가 계속 공란으로 표시되면 폰트 매핑 외의 문자열 인코딩/렌더링 경로를 추가로 확인해야 합니다.

## 주의

이 파일은 현재 한국어화 작업 과정에서 검증 중인 WIP 설정입니다. Temple+ 업데이트나 다른 폰트 설정과 충돌할 수 있으므로 기존 `mapping.json`을 반드시 백업해 두는 것을 권장합니다.
