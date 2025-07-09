
한투증 깃
https://github.com/koreainvestment/open-trading-api/tree/main
문서화된놈
https://wikidocs.net/159297

auto trader
https://github.com/kieran-mackle/AutoTrader

token 인증은 1분에 한번 날릴 수 있음.
24시간 후에 만료되고, 6시간 이내에는 요청 시 같은 토큰이 오게 됨.

# 한투증 API 분석
##  [국내주식] 기본시세 > 주식현재가 시세 (종목번호 6자리)
```python
rt_data = kb.get_inquire_price(itm_no="071050")
```

### result data
<details>
<summary> result data </summary>
- stck_shrn_iscd: 주식 단축 종목코드 (예: "071050")
- rprs_mrkt_kor_name: 대표 시장 한글명 (예: "KOSDAQ", "KOSPI")
- bstp_kor_isnm: 업종명 (예: "소프트웨어")
- iscd_stat_cls_code: 종목 상태 구분 코드 (00:정상, 55:정지, 58:정리매매 등)

#### 가격 정보 (핵심)
- stck_prpr: 주식 현재가 (현재 체결된 가격)
- prdy_vrss: 전일 대비 등락 (어제 종가 대비 얼마나 올랐거나 내렸는지, 예: "-500")
- prdy_vrss_sign: 전일 대비 부호 (1:상한, 2:상승, 3:보합, 4:하한, 5:하락)
- prdy_ctrt: 전일 대비율 (어제 종가 대비 등락률, 예: "-3.21")
- stck_oprc: 시가 (오늘 장 시작 가격)
- stck_hgpr: 고가 (오늘 장 중 가장 높았던 가격)
- stck_lwpr: 저가 (오늘 장 중 가장 낮았던 가격)
- stck_mxpr: 상한가 (오늘 오를 수 있는 최대 가격)
- stck_llam: 하한가 (오늘 내릴 수 있는 최대 가격)
- stck_sdpr: 기준가 (오늘의 상한가/하한가를 계산하는 기준 가격, 보통 어제 종가)
- wghn_avrg_stck_prc: 가중 평균 주가 (거래량을 고려한 평균 체결 가격)

#### 거래량/거래대금 정보
- acml_vol: 누적 거래량 (오늘 하루 동안 거래된 총 주식 수)
- acml_tr_pbmn: 누적 거래 대금 (오늘 하루 동안 거래된 총 금액)
- prdy_vrss_vol_rate: 전일 대비 거래량 비율 (어제 같은 시간까지의 거래량 대비 오늘 거래량 비율)

#### 투자자 정보
- frgn_hldn_qty: 외국인 보유 수량 (외국인이 보유한 총 주식 수)
- hts_frgn_ehrt: HTS 외국인 소진율 (외국인이 취득 가능한 최대 주식 수 대비 현재 보유 비율)
- frgn_ntby_qty: 외국인 순매수 수량 (오늘 외국인의 (매수 수량 - 매도 수량))
- pgtr_ntby_qty: 프로그램 순매수 수량 (프로그램 매매의 순매수 수량)

#### 재무/가치 지표
- hts_avls: 시가총액 (단위: 억)
- lstn_stcn: 상장 주식 수
- cpfn: 자본금 (단위: 원)
- stck_fcam: 주식 액면가
- per: PER (주가수익비율) (시가총액 / 당기순이익)
- pbr: PBR (주가순자산비율) (시가총액 / 자본총계)
- eps: EPS (주당순이익) (당기순이익 / 주식 수)
- bps: BPS (주당순자산) (자본총계 / 주식 수)
- vol_tnrt: 거래량 회전율
- stac_month: 결산 월 (회계연도가 끝나는 달)

#### *기간별 가격 정보
- d250_hgpr: 250일 최고가
- d250_hgpr_date: 250일 최고가 달성일
- d250_lwpr: 250일 최저가
- d250_lwpr_date: 250일 최저가 달성일
- w52_hgpr: 52주(1년) 최고가
- w52_hgpr_date: 52주 최고가 달성일
- w52_lwpr: 52주(1년) 최저가
- w52_lwpr_date: 52주 최저가 달성일
- stck_dryy_hgpr: 연중 최고가
- stck_dryy_lwpr: 연중 최저가

#### 시장 조치 및 상태 정보
- mrkt_warn_cls_code: 시장 경고 구분 코드 (00:없음, 01:투자주의, 02:투자경고, 03:투자위험)
- invt_caful_yn: 투자주의 환기 종목 여부 (Y/N)
- mang_issu_cls_code: 관리종목 구분 코드
- ssts_yn: 매매정지 여부 (Y/N)
- sltr_yn: 정리매매 종목 여부 (Y/N)
- short_over_yn: 공매도 과열 종목 여부 (Y/N)
- vi_cls_code: VI(변동성 완화장치) 발동 구분 코드
- crdt_able_yn: 신용 거래 가능 여부 (Y/N)
- marg_rate: 증거금률 (신용거래 시 필요한 현금 비율)
</details>


# 구현되어야 할 기능들.
## 거래
> 실제 거래에 필요할 것 같은 기능들.
- 주식 종목 검색 기능. top 30? 같은거
- 종목을 queue에 넣고, 큐를 돌리며 매수/매도 지표 확인.
- MACD, RSI 등의 보조지표는 API에 없고, 직접 일봉을 가져와서 만들어야함.


## 분석
> 사람이 보고 판단하기 위함.
- 그래프화
- 산 시점 ~ 판 시점 표시


## 백테스팅
- 이전 특정 시점의 가격 불러오기.
- 이걸 위해서, 로직과 로직을 호출하는 부분이 완벽하게 분리되어야 함.
    - 메인 실행부에서 백테스트의 경우 무수히 차트를 호출하고 주입해주어야 함.