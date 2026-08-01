# Third-Party Notices

This project separates original code from third-party software and public data.
The application runtime uses only datasets whose official pages state
`이용허락범위 제한 없음`. Source names and original links remain visible in
the service and data registry.

## Public Data Used At Runtime

| Provider | Dataset | Official terms |
|---|---|---|
| 금융위원회 | 금융용어사전 | 이용허락범위 제한 없음 |
| 예금보험공사 | 착오송금 반환지원제도 FAQ, 예금보험 용어사전, 부보금융회사 목록 | 이용허락범위 제한 없음 |
| 서민금융진흥원 | 대표 FAQ, 미소금융 지점, 연령대별 대출실적 | 이용허락범위 제한 없음 |
| 공정거래위원회 | 전화권유판매사업자, 소비자 모범상담 사례 | 이용허락범위 제한 없음 |
| 경찰청 | 보이스피싱 현황, 시도청별 피해금액 | 이용허락범위 제한 없음 |
| 우체국금융개발원 | 우체국 금융 사기계좌 정보 | 이용허락범위 제한 없음 |

Exact URLs, update dates, row counts, and usage purposes are recorded in
`backend/app/data/official/official_dataset_registry.json`.

## Excluded Or Reference-Only Material

- 한국언론진흥재단 뉴스빅데이터 메타데이터: 공공누리 제4유형으로
  상업적 이용과 변경이 금지되어 runtime and distribution에서 제외했습니다.
- 출처·이용조건이 확인되지 않은 사용자 제공 PDF: runtime에서 제외했습니다.
- 공정거래위원회 표준약관 원문과 설명회 PDF 추출본: 원문 재배포 대신 공식
  페이지 링크와 프로젝트가 직접 작성한 소비자 점검 기준만 사용합니다.

## Software Libraries

The frontend primarily uses Next.js, React, Lucide React, and qrcode.react.
The backend primarily uses FastAPI, Uvicorn, Pydantic, Requests, pypdf,
Pillow, pytesseract, and faster-whisper. These packages retain their own
MIT, BSD, Apache, ISC, LGPL, or other notices. When distributing a bundled
binary or container, preserve the dependency license files and this notice.
