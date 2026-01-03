# OpenFrame 이슈 검색 결과

**검색일**: 2026-01-03
**검색 쿼리**: `TPETIME error`
**검색 제품**: OpenFrame
**검색 결과**: 10개 이슈 발견

---

## 📊 검색 결과 요약

| Issue ID | 제목 | 상태 | 우선순위 | 등록일 |
|----------|------|------|----------|--------|
| 347863 | [Project] [일본 동경해상] TPETIME 에러 분석 및 가이드 문의 | Closed | Normal | 2025/10/17 18:12:14 |
| 344218 | [일본 이나게야] 대화형 트랜잭션에서 timeout이 발생하는 현상 | Approved | High | 2025/07/14 13:45:05 |
| 339659 | [일본 후지생명] aimcmd 에 메세지가 없는 경우에 대해 문의드립니다. | Closed | Normal | 2025/03/07 10:52:00 |
| 337468 | [Project] [일본 우오이치] ndbunloader의 성능개선 요청드립니다. | Closed_P | Normal | 2025/01/08 09:22:09 |
| 336450 | [일본 IJTT] CONSOLE처리중 에러현상에 대해 확인부탁드립니다. (현재 고객 장애상 | Assigned | Normal | 2024/12/06 10:49:47 |
| 326554 | [내부이슈/postgre] oscdown -r 시 timeout(TPETIME) 발생하는  | Closed_P | Normal | 2024/06/18 15:04:40 |
| 326216 | [Internal] [내부이슈/postgre] oscdown -r 시 timeout(TPE | Closed_P | Normal | 2024/06/12 11:15:35 |
| 326002 | [Project] [일본 우오이치] NDB UNLOADER COBOL 생성시 GET FIR | Closed_P | Normal | 2024/06/07 13:38:11 |
| 325259 | [내부이슈/postgre] oscdown -r 시 timeout(TPETIME) 발생하는  | Closed_P | Normal | 2024/05/24 18:48:26 |
| 322743 | [일본 손보재팬] MPP가 기동되지 않은 상태에서 큐잉된 건에 대하여 MPP가 기동되었을때 | Closed_P | High | 2024/04/17 11:06:57 |

---

## 🔥 주요 이슈 #336450 (진행중)

### 📌 이슈 개요

**제목**: [일본 IJTT] CONSOLE처리중 에러현상에 대해 확인부탁드립니다. (현재 고객 장애상황입니다.)
**상태**: Assigned
**우선순위**: Normal
**담당자**: 김예진C ( yeajin_kim2@tmaxsoft.com)
**제품**: OpenFrame Batch

### 🐛 이슈 내용

안녕하세요 일본 IJTT진행중인 김성일입니다. 현재 고객사 CONSOLE에서 장애가 발생하고 있어서 확인을 부탁드립니다.아래와 같이 cmsvr가 처리를 못하는 상황이 계속 발생하고 있습니다.해당 건으로인해 console이 멈춰 버리는데 대응방법이 필요합니다. top을 보면 cmsvr이 100%가 되는 현상이 오전 9시에 확인했으며 큐가 쌓여있었는데 time out으로 인해 큐가 풀리면서 해소가 되었으나 그 이후 가끔 아래와 같은 현상이 발생되고 있습니다. 로그를 요청중입니다만 그전에 필요한 부분은 사진을 찍었습니다. 문제의 원인과 해결할 수 있는 방법을 알려주시면 감사하겠습니다. [에러 로그]DSNAME('KPRPSD05.WK390') NEW SPACE(150 50) BLOCK(22932) VOLUME(SYS024) RELEASE] returned 0           ASCFILE   DDNAME(SYSOUT)   REUSE DSNAME('KPRPSD05.WKERR') SHR KEEP                                             [2024-12-06T09:36:32.280665] [KEQEFT01(1020467)       ] [M] [TSO0201M] ASCFILE start. [2024-12-06T09:36:32.291744] [KEQEFT01(1020467)       ] [M] [TSO0202M] allocate completed - ds=KPRPSD05.WKERR,dd=SYSOUT [2024-12-06T09:36:32.291773] [KEQEFT01(1020467)       ] [M] [TSO0009M] TSO command [ASCFILE   DDNAME(SYSOUT)   REUSE DSNAME('KPRPSD05.WKERR') SHR KEEP] returned 0           EXCPGM    K810D150  FILE('KMK.LOAD')                           [2024-12-06

### 💡 해결 방안

**Sungil Kim** ():
12월 5일에 disk full로 인해 서버를 재 기동했습니다만 해당 건이 영향이 있을까요 ???

**Sungil Kim** ():
CLIENT ID 747 IS NOT FOUND는 어떤 에러인가요 ?시간때를 보면 해당 에러때문인 것 같습니다만

**Sungil Kim** ():
SLOG가 도착하여 첨부합니다.

---

## 📋 관련 이슈

### 이슈 #322743 (해결됨)

**제목**: [일본 손보재팬] MPP가 기동되지 않은 상태에서 큐잉된 건에 대하여 MPP가 기동되었을때 처리하는 기능 추가 요청

안녕하십니까일본법인의 윤영성입니다.MPP가 STOP되어있는 상태에서 큐잉이 되었을때 해당 MPP가 기동되었을때 쌓여있는 큐잉을 처리하는 기능추가를 요청드립니다.감사합니다....

### 이슈 #325259 (해결됨)

**제목**: [내부이슈/postgre] oscdown -r 시 timeout(TPETIME) 발생하는 현상

안녕하세요 GBSC 4 파트 이명신입니다.oscdown -r 사용 시 아래와 같이 에러 발생합니다.>oscdown -r OSCOIVP1OSCDOWN : OSC PLTPI closing(OSCOIVP1)                                 [ OK ]OSCDOWN : OSC tranclass server(OSCOIVP1_ABC1)                         (E) TMM2135 failed to read data from Tmax process [PROC0304Connection reset by ...

### 이슈 #326002 (해결됨)

**제목**: [Project] [일본 우오이치] NDB UNLOADER COBOL 생성시 GET FIRST WITHIN RANGE구 예외처리를 부탁드립니다. (이슈 분리 #322573)

수고하십니다 일본 법인 조민제입니다.게제의 건 관련해 ndbunloader 시 생성되는 RECORD COBOL 파일을 이용하여 UNLOAD 시 데이터가 0인 NDB에 대해서 PROGRAM이 강제 종료됩니다.SQL> select * from SCHSYHN_KESBRT;0 row selected.SYHNRECS.COBOL 상세한 내용은 Action No.2067065 기재하였습니다.Issue Number : 322573 | Action No. 2067065 | Registrant : Minje Jo | Registered date : ...

---

## 🎯 결론

### COBOL 현황

1. **주요 이슈 1건 진행 중**
   - [일본 IJTT] CONSOLE처리중 에러현상에 대해 확인부탁드립니다. (현재 고객 장애상황입니다.)

2. **과거 유사 이슈 2건 해결 완료**

3. **향후 대응 방향**
   - 진행 중인 이슈 모니터링
   - 해결된 이슈의 패치 적용 여부 확인
   - 유사 문제 재발 방지를 위한 가이드 정립

---

**보고서 작성일**: 2026-01-03
**작성자**: IMS Report Generator (자동 생성)
**데이터 출처**: TmaxSoft IMS (https://ims.tmaxsoft.com)
