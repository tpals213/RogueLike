# 로그라이트 오토배틀러 (프로토타입)

죽어도 사라지지 않는 메타 자원(다이아)으로 영구 성장하며 점점 강해지는 로그라이트 + 오토배틀 게임.
전투는 100% 자동 진행되고, 플레이어는 전투 전 장비/시너지 세팅과 맵 경로 선택에만 개입한다.

## 실행 방법

콘솔(그래픽 없이 텍스트로 플레이) 버전은 별도 설치 없이 바로 실행된다.

```bash
python3 play.py         # 직접 번호 입력하며 플레이
python3 play.py --auto  # 무작위 자동 진행 (검증용)
```

tcod 기반 GUI 버전은 가상환경에 `tcod`를 설치해야 한다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python gui.py
```

GUI는 숫자키(1~9)로 선택, 스페이스/엔터로 다음 진행, ESC로 종료.
한글 폰트는 macOS 시스템 폰트(AppleGothic 등)를 자동으로 찾아서 로드한다 — 다른 OS에서는 `gui.py`의
`KOREAN_FONT_CANDIDATES`에 폰트 경로를 추가해야 한글이 보인다.

**모바일(안드로이드 APK) 배포를 목표로 하는 Kivy 버전**은 `mobile_app.py`다. 가상환경에 `kivy`를
설치해야 한다 (`requirements.txt`에 포함됨).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python mobile_app.py
```

데스크톱에서도 폰 세로 화면 비율(420x800)로 창이 뜨며, 버튼 탭으로만 진행한다(키보드 입력 없음).
이미지 에셋 없이 색상 도형으로만 인터페이스를 구성했고, `game/` 로직은 콘솔/tcod 버전과 완전히
동일하게 재사용한다. 세이브 경로는 `Kivy App.user_data_dir` 기준이라 콘솔/GUI 버전의 `saves/`와는
별도 위치에 저장된다.

한글은 `assets/fonts/NotoSansKR-Regular.ttf`(Google Noto Sans KR, OFL 라이선스, 가변폰트를
정적 인스턴스로 변환한 것 — `assets/fonts/NOTICE.md` 참고)를 번들로 포함해서 데스크톱/APK 어디서든
동일하게 렌더링된다.

**안드로이드 APK 빌드**는 `buildozer`로 한다 (`pip install buildozer cython`, 그리고 macOS는
`brew install autoconf automake libtool pkg-config cmake` + JDK 17 필요 — python-for-android가
정확히 JDK 17만 지원하며, `/usr/bin/javac`가 인식하도록 `/Library/Java/JavaVirtualMachines/`에
심볼릭 링크로 등록해야 한다).

```bash
source .venv/bin/activate
JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home" buildozer -v android debug
```

`main.py`는 이미 전투 스모크 테스트 스크립트가 쓰고 있어서(아래 참고), buildozer의 소스 디렉터리는
저장소 루트가 아니라 `mobile_build/`로 지정했다 — `mobile_build/main.py`, `mobile_build/game`,
`mobile_build/assets`는 각각 `mobile_app.py`, `game/`, `assets/`를 가리키는 심볼릭 링크일 뿐,
실제 코드는 전부 저장소 루트에 그대로 있다 (`buildozer.spec`의 `source.dir` 참고).

빌드 결과물은 `bin/*.apk`. 폰에 설치하려면 USB 디버깅 연결 후 `adb install bin/*.apk`, 또는
APK 파일을 폰으로 옮겨서(에어드랍/클라우드 등) 직접 열어 설치(출처를 알 수 없는 앱 설치 허용 필요).

허브(영구 특성 상점)는 콘솔/GUI 버전에서는 별도 스크립트로 실행한다 (`mobile_app.py`는 앱 안에
메인 메뉴로 통합돼 있음).

```bash
python3 hub.py         # 직접 특성 id 입력해서 다이아로 구매
python3 hub.py --auto  # 살 수 있는 특성을 무작위로 다 구매 (검증용)
```

전투 로직만 빠르게 확인하고 싶으면 `python3 main.py` (맵 없이 몬스터 몇 마리와 순차 전투만 도는 스모크 테스트).

## 프로젝트 구조

```
game/
  models.py       # Stats, Item, Character, Monster, Relic 등 기본 데이터 구조
  synergy.py       # 장비 태그 시너지 (독/화염/버서커/얼음/마나, 3/5/7 스택)
  relics.py         # 유물 효과를 전투 스탯/흐름에 반영
  combat.py          # 자동 전투 판정 (데미지 계산, 상태이상, 오버킬)
  content.py          # 캐릭터/몬스터/아이템/유물 데이터 (3개 장 분량)
  mapgen.py            # 장(Act)별 노드맵 생성 (갈림길 그래프)
  shop.py               # 상점 진열 목록 생성
  hub.py                 # 다이아로 사는 영구 특성 트리
  save_system.py          # 메타 저장(다이아/해금 특성) JSON 입출력
main.py       # 전투 로직 스모크 테스트
play.py       # 콘솔(텍스트) 버전 플레이 진입점
gui.py        # tcod GUI 버전 플레이 진입점
hub.py        # 허브(특성 상점) 콘솔 진입점
mobile_app.py # Kivy 버전 플레이 진입점 (모바일 배포 목표, 메인 메뉴 + 허브 통합)
```

## 현재 구현 상태

**완성**
- 3개 장(숲/폐허 → 설산/동굴 → 화산/성채) 구성, 장마다 24~28개 노드로 랜덤 갈림길 맵 생성
- 노드 타입: 일반/엘리트/상점/우물/이벤트/축복/보스/유물방
- 도입부는 일반전투 3회(선택지 있음) + 상점·우물·이벤트 중 2개가 반드시 섞이도록 구조적으로 보장 —
  엘리트는 이 구간 이후에만 등장 가능
- 장비 7슬롯(투구/왼손/오른손/갑옷/신발/목걸이/반지), 일반(태그 1개)/희귀(태그 2개) 등급, 슬롯×등급별
  최소 4종씩 아이템 56종
- 시너지 5종(독/화염/버서커/얼음/마나) × 3/5/7 스택 임계값
- 유물 21종, 전부 전투 로직에 실제 효과 연결됨 (플라시보 없음)
- 자원: 골드(런 한정) / 다이아(영구, 일반·엘리트 처치·노드 클리어·오버킬로 산정)
- 일반전투 승리 시 골드 + 일반등급 아이템 3택1(스킵 가능), 엘리트 승리 시 골드 + 희귀등급 아이템
  3택1(스킵 가능) + 무작위 유물
- 상점은 골드로 리롤 가능(품절 슬롯만 새 아이템으로 채워짐), 구매한 항목은 품절 처리되어 재구매 불가
- 허브 특성 트리(HP/물공/마공 각 5단계, 하위 단계 구매해야 다음 단계 해금)
- 도적 스타터 클래스, 오른손 무기 1개로 시작
- 콘솔(`play.py`), tcod GUI(`gui.py`), Kivy 모바일(`mobile_app.py`) 세 진입점 모두 동일한 `game/`
  로직을 공유
- Kivy 버전은 `buildozer`로 안드로이드 APK 빌드까지 확인됨 (`bin/*.apk`)

**미완성 / 스텁**
- 전사·마법사는 이름만 등록, 스킬/밸런스 미작업, 해금 기능도 아직 없음 (다이아 소비처 미구현)
- 상점 가격/보상 수치, 몬스터 스탯, 시너지 수치 전부 초기 플레이스홀더 — 밸런싱 전
- 캐릭터/몬스터/아이템 그래픽 없음 (색상/텍스트 기반 인터페이스만 존재) — 추후 AI 생성 이미지로 대체 예정
- 보스 멀티페이즈 패턴 없음
- APK는 디버그 서명 빌드만 확인됨 — 실 배포(스토어 등록, 릴리스 서명, OFL 라이선스 전문 동봉)는 별도 작업

## 개발 원칙

- 유료 서비스/구독/API 없이 전부 무료 오픈소스 도구로 개발 (Python, tcod, Kivy)
- 저장은 로컬 JSON 파일만 사용, 서버/클라우드/DB 없음
