# OpenFrame 이슈 검색 결과

**검색일**: 2026-01-03
**검색 쿼리**: `OpenFrame에서 TPETIME 에러 발생 원인과 대응방안`
**검색 제품**: OpenFrame
**검색 결과**: 33개 이슈 발견

---

## 📊 검색 결과 요약

| Issue ID | 제목 | 상태 | 우선순위 | 등록일 |
|----------|------|------|----------|--------|
| 348115 | My Page - Customize My Page - Manage Filters - Set | Closed_P | Normal | 2025/10/24 17:56:58 |
| 348115 | My Page - Customize My Page - Manage Filters - Set | Closed_P | Normal | 2025/10/24 17:56:58 |
| 348115 | My Page - Customize My Page - Manage Filters - Set | Closed_P | Normal | 2025/10/24 17:56:58 |
| 348115 | My Page - Customize My Page - Manage Filters - Set | Closed_P | Normal | 2025/10/24 17:56:58 |
| 348115 | Subject [Project] [일본 SUMINOE] DAM RELATIVE KEY 로  | Closed_P | Normal | 2025/10/24 17:56:58 |
| 348115 | Product Notice | Closed_P | Normal | 2025/10/24 17:56:58 |
| 348115 | [Project] [일본 SUMINOE] DAM RELATIVE KEY 로 WRITE 동작 | Closed_P | Normal | 2025/10/24 17:56:58 |
| 348115 | [Project] [일본 SUMINOE] DAM RELATIVE KEY 로 WRITE 동작 | Closed_P | Normal | 2025/10/24 17:56:58 |
| 347878 | My Page - Customize My Page - Manage Filters - Set | Assigned | Normal | 2025/10/20 10:19:40 |
| 347878 | [일본 우오이치] ofmanager 에서 NDB set 화면의 검색기록 확인 할 수 있도록 | Assigned | Normal | 2025/10/20 10:19:40 |
| 346525 | [일본 후지생명] ABEND시의 재기동이 되지 못한 문제가 발생되었습니다. | Assigned | Normal | 2025/09/05 09:31:00 |
| 345421 | [일본 우오이치] ofmanager 에서 NDB set 화면의 검색기록 확인 할 수 있도록 | Closed_P | Normal | 2025/08/11 10:25:28 |
| 344906 | [Project] [US/Colony Brand] DD not found after PGM | Closed | Normal | 2025/07/29 07:13:06 |
| 344906 | [Project] [US/Colony Brand] DD not found after PGM | Closed | Normal | 2025/07/29 07:13:06 |
| 322210 | [US/Project/Sears] OSIMPPSVR server crash | Closed | Normal | 2024/04/09 09:32:35 |
| 322210 | [US/Project/Sears] OSIMPPSVR server crash | Closed | Normal | 2024/04/09 09:32:35 |
| 319755 | [Project] [일본 우오이치] not supported key2 in text uni | Closed_P | Normal | 2024/03/04 11:55:19 |
| 319755 | [Project] [일본 우오이치] not supported key2 in text uni | Closed_P | Normal | 2024/03/04 11:55:19 |
| 318260 | [US/Project/Sears] guide for building MySQL XA ser | Closed_P | High | 2024/02/05 09:52:28 |
| 317972 | [PoC] [일본 미츠이카드] asm DYNALLOC 동작에 대해서 질문입니다. | Closed | Normal | 2024/01/30 13:18:56 |
| 317972 | [PoC] [일본 미츠이카드] asm DYNALLOC 동작에 대해서 질문입니다. | Closed | Normal | 2024/01/30 13:18:56 |
| 282859 | [Project] [US/Project/FBB] unsupported verb code f | Closed_P | Normal | 2022/05/18 20:22:03 |
| 282859 | [Project] [US/Project/FBB] unsupported verb code f | Closed_P | Normal | 2022/05/18 20:22:03 |
| 346525 |  |  |  |  |
| 347878 |  |  |  |  |
| 348115 |  |  |  |  |
| 348115 |  |  |  |  |
| 349871 |  |  |  |  |
| 350120 |  |  |  |  |
| 350173 |  |  |  |  |
| 350334 |  |  |  |  |
| **350137** | [Project] [일본 동경해]SVC99(DYNALLOC) 동작 이슈에 대한 패치 제공  | **Assigned** | **High** | 2025/12/23 17:33:11 |
| **350137** | [Project] [일본 동경해]SVC99(DYNALLOC) 동작 이슈에 대한 패치 제공  | **Assigned** | **High** | 2025/12/23 17:33:11 |

---

## 🔥 주요 이슈 #350137 (진행중 - HIGH Priority)

### 📌 이슈 개요

**제목**: [Project] [일본 동경해]SVC99(DYNALLOC) 동작 이슈에 대한 패치 제공 요청
**상태**: Assigned
**우선순위**: High
**담당자**: 이민성 ( minseong_lee@tmaxsoft.com)
**제품**: OpenFrame ASM

### 🐛 이슈 내용

※작성 전 Product Notice 를 참고 하세요.※안녕하세요.일본법인 문성호입니다.OpenFrame ASM 환경에서 SVC99 매크로(DYNALLOC) 동작과 관련된 이슈가 확인되어,해당 건에 대한 패치 제공 가능 여부 검토를 요청드립니다.본 이슈는 업무 영향도가 높은 중요 이슈로 판단되어,가능하시다면 우선순위를 높게 확인해 주시면 감사하겠습니다.확인에 필요한 추가 정보가 있다면 말씀 주시기 바랍니다.감사합니다.1. 이슈 설명SVC99 매크로(DYNALLOC) 실행 시 설정되는 상세 리턴코드가호스트 환경과 달리 OpenFrame 환경에서는 정상적으로 설정되지 않는 문제가 발생하고 있습니다.호스트에서는 IDCAMS 실행 결과에 따라 SVC99 상세 리턴코드가 정상적으로 세트되며,이를 기반으로 상위 ASM 프로그램(PZS555)에서 정상/비정상 여부를 판단합니다.그러나 OpenFrame 환경에서는 동일한 조건에서 SVC99 상세 리턴코드가 NULL 값으로 확인되었으며,이로 인해 원래 정상 종료되어야 할 시나리오가 에러 처리로 분기되는 현상이 발생합니다.2. 제품 버전OpenFrame ASM v4 1676 32bit3. 이슈 환경redhat 9.4 OpenFrame 32bit4. 이슈 절차1. 데이터셋 삭제용 카탈로그 프로그램(DADEL)에서 ASM 프로그램 PZS555 실행2. PZS555 내부에서 IDCAMS 호출3, 삭제 대상 데이터셋이 존재하지 않아 IDCAMS가 RC≠0으로 종료(※ 이 시점까지는 호스트/OF 동일한 정상 동작)4. PZS555는 IDCAMS의 RC≠0일 경우 SVC99(DYNALLOC)를 호출하여 상세 리턴코드를 확인5. 호스트 환경에서는 상세 리턴코드가 정상적으로 세트되어 해당 케이스를 정상 종료 처리    OpenFrame 환경에서는 상세 리턴코드가 NULL로 설정되어 에러 처리로 종료됨5. 기대 결과호스트와 동일한 결과(상세 리턴코드가 정상적으로 세트되어 해당 케이스를 정상 종료 처리)6. 현재 결과OpenFrame 환경에서는 

### 💡 해결 방안

**이지우** ():
안녕하세요.  정준호 연구원님해당 기능 지원 여부 검토 요청 드립니다.감사합니다.

**김도환** ():
안녕하세요 OF1팀 김도환입니다.해당 동경해상 문의는 비호환으로 답변이 나갔습니다만, 전무님 요청으로 PATCH를 제공 받을 수 있는지 검토 부탁 드립니다.IBM 문의 및 답변 입니다.「SVC99マクロ(DYNALLOC)」に対する詳細リターンコードに対して、ホストと同様の値がセットされていない。これはOpenFrameの製品バグなのか、非互換項目なのかを教えてください。SVC99 매크로(DYNALLOC)'에 대한 상세 리턴 코드에 대해 호스트와 동일한 값이 세팅되어 있지 않다.이것은 OpenFrame의 제품 버그인지 비호환 항목인지 알려주세요.PS답변 내용ofasm에서는 DYNALLOC 기능을 지원하고 있으나, 현재 시나리오에서 사용중인 DYNALLOC 기능은 allocation 시 DALRTORG 를 요구하고 있습니다. 이는 현재 비호환 사항으로 지원하고 있지 않아 프로그램이 종료된 것입니다.기본적으로 지원중인 DYNALLOC 기능 중에 실패 시에는 프로그램이 종료되지 않고 리턴 value를 넘겨주

**이지우** ():
안녕하세요.  문성호 매니저님이슈 상황 설명이 좀 달라서 정정 합니다. SVC99 매크로(DYNALLOC) 실행 시 설정되는 상세 리턴코드가호스트 환경과 달리 OpenFrame 환경에서는 정상적으로 설정되지 않는 문제가 발생하고 있습니다 SVC99 매크로(DYNALLOC) 실행 시 Key Field 값 중에 현재 OFASM에서 지원하지 않는 Key 값이 있어서 Allocate가 정상적으로 되지 않고 에러가 나서 중단된 JOB 입니다. 감사합니다.

---

## 📋 관련 이슈

### 이슈 #282859 (해결됨)

**제목**: [Project] [US/Project/FBB] unsupported verb code found in SVC 99

안녕하세요 한장원입니다.SVC 99에 대해 미지원 verb code 발견되어 이슈 등록합니다.1. 배경1.1 ofasm 버젼oframe@devue1ofapp01:/opt/tmaxapp/ASM_COMPILE/QIOMGR.asm_v_tmaxsoft_ph_20220513_145013>ofasm --versionOpenFrame Assembler 4Revision: 1285CommitID: e1fbf951.2 SVC 99 verb codehttps://www.ibm.com/docs/en/zos/2.2.0?topic=rdaf-svc-99-p...

### 이슈 #282859 (해결됨)

**제목**: [Project] [US/Project/FBB] unsupported verb code found in SVC 99

안녕하세요 한장원입니다.SVC 99에 대해 미지원 verb code 발견되어 이슈 등록합니다.1. 배경1.1 ofasm 버젼oframe@devue1ofapp01:/opt/tmaxapp/ASM_COMPILE/QIOMGR.asm_v_tmaxsoft_ph_20220513_145013>ofasm --versionOpenFrame Assembler 4Revision: 1285CommitID: e1fbf951.2 SVC 99 verb codehttps://www.ibm.com/docs/en/zos/2.2.0?topic=rdaf-svc-99-p...

### 이슈 #317972 (해결됨)

**제목**: [PoC] [일본 미츠이카드] asm DYNALLOC 동작에 대해서 질문입니다.

안녕하세요. 일본법인 유 혜빈입니다.POC자산인 DYNALLOC ams을 확인도중, 아래와 같은 에러가 발생하고있으나, 해당 에러원인을 파악하지 못해, 발생하는 원인에 대해서 확인부탁드립니다. > DYNALLOC: verb code = 0 not implementedASM자산 및 SPOOL첨부합니다.추가로 확인이 필요한 자산이 있으면 연락부탁드립니다.▼ JOB00824 SPOOL 일부분  *** MEAS020.COBOL START ***  *** MEAS020.COBOL(LINKAGE) : ＸＸサブスキーマ名 [SSHLB03 ]  *...

---

## 🎯 결론

### ABEND시의 현황

1. **주요 이슈 1건 진행 중**
   - [Project] [일본 동경해]SVC99(DYNALLOC) 동작 이슈에 대한 패치 제공 요청
   - 업무 영향도 높음 (High Priority)

2. **과거 유사 이슈 2건 해결 완료**

3. **향후 대응 방향**
   - 진행 중인 이슈 모니터링
   - 해결된 이슈의 패치 적용 여부 확인
   - 유사 문제 재발 방지를 위한 가이드 정립

---

**보고서 작성일**: 2026-01-03
**작성자**: IMS Report Generator (자동 생성)
**데이터 출처**: TmaxSoft IMS (https://ims.tmaxsoft.com)
