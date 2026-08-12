# TemplePlus 1.0.98 Korean legacy text hooks

이 디렉터리는 `GrognardsFromHell/TemplePlus`의 `v1.0.98` 소스를 기준으로 한국어 레거시 문자열 경로를 보완하기 위한 테스트 패치입니다.

현재 Core 테스트 범위:

- `0x10073A30` 성별 이름 → `stat.mes` 4000/4001
- `0x10073B40` 성향 짧은 설명 → `stat.mes` 16000 + alignment
- `0x10073C20` 파티 성향 이름 → `stat.mes` 6000 + alignment
- `0x1001FA80` NPC/오브젝트 표시명 → TemplePlus `description.mes` 조회 경로
- `Infrastructure/stringutil.cpp` → UTF-8 엄격 검증 후 CP949 fallback

한국어를 실행 파일에 하드코딩하지 않고, 이미 번역된 `stat.mes` / `description.mes`를 원본 레거시 UI가 읽도록 연결하는 것이 목적입니다.

## 자동 빌드

브랜치 `templeplus-kr-legacy-hooks`의 GitHub Actions `Build TemplePlus KR Runtime Test`는 다음 순서로 동작합니다.

1. 공식 TemplePlus `v1.0.98` 소스를 clone
2. `apply_kr_stringutil_patch.py` 적용
3. `apply_kr_legacy_text_hooks_core.py` 적용
4. Win32 Release 빌드
5. `TemplePlus_1.0.98_KR_LegacyHooks_CORE_TEST.zip` artifact 업로드

## 테스트 순서

1. 기존 실험 `TemplePlus.exe`를 백업합니다.
2. 실제 게임 폴더의 `data/mes/stat.mes`, `pc_creation.mes`, `description.mes`를 한국어 CP949 버전으로 복구합니다.
3. Actions artifact의 `TemplePlus.exe`를 TemplePlus `app-1.0.98` 폴더에 넣습니다.
4. 새 게임 → 파티 성향 9개를 확인합니다.
5. 캐릭터 생성에서 성별/성향 요약을 확인합니다.
6. NPC 마우스오버 이름을 확인합니다.

Bark는 Core 검증 후 별도 단계로 진행합니다. 첫 Core 빌드에서는 `0x100A2200` text-floater renderer를 수정하지 않습니다.
