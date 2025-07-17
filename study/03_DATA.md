# 데이터 얻기

## 증권사 API 활용

### 못알아먹을 KIS 변수명 매핑
| 컬럼명 | 매핑된 정보 | description |
| ----- | ---- | ----------|
| stck_bsop_data | data | 주식 영업일자 |
| stck_oprc | open | 주식 시가 |
| stck_hgpr | high | 주식 고가 |
| stck_lwpr | low | 주식 저가 |
| stck_clpr | close | 주식 종가 |
| acml_vol | volume | 누적 거래량 |


### KIS API response 분석
| 제목 뭔뜻임?
| kis api 이름 : 대응되는 새로 만든 api 이름

#### get_inquire_daily_price : get_daily_price

#### get_inquire_daily_itemchartprice : get_itempricechart_1, get_itempricechart_2
<details>
<summary>output1 | 현재가 종합 정보</summary>

**가격 관련**
- stck_prpr: 현재가 (66,700원)
- stck_prdy_clpr: 전일 종가 (64,700원)
- stck_oprc: 당일 시가 (65,900원)
- stck_hgpr: 당일 고가 (66,800원)
- stck_lwpr: 당일 저가 (64,400원)
- stck_prdy_oprc: 전일 시가 (63,700원)
- stck_prdy_hgpr: 전일 고가 (64,700원)
- stck_prdy_lwpr: 전일 저가 (63,100원)
    
**등락 관련**
- prdy_vrss: 전일 대비 등락 (2,000원)
- prdy_vrss_sign: 전일 대비 부호 (2:상승, 5:하락)
- prdy_ctrt: 전일 대비율 (3.09%)

**거래 관련**
- acml_vol: 당일 누적 거래량 (39,448,683주)
- acml_tr_pbmn: 당일 누적 거래대금 (2,597,601,930,887원)
- prdy_vol: 전일 거래량 (23,042,660주)
- prdy_vrss_vol: 전일 대비 거래량 (16,406,023주)
- vol_tnrt: 거래량 회전율 (0.67%)

**호가 관련**
- askp: 매도호가 (66,700원)
- bidp: 매수호가 (66,600원)

**종목 정보**
- hts_kor_isnm: 종목명 (삼성전자)
- stck_shrn_iscd: 종목코드 (005930)
- stck_mxpr: 상한가 (84,100원)
- stck_llam: 하한가 (45,300원)

**기업 정보**
- stck_fcam: 액면가 (100원)
- lstn_stcn: 상장주식수 (5,919,637,922주)
- cpfn: 자본금 (7,780억원)
- hts_avls: 시가총액 (3,948,398억원)

**투자지표**
- per: PER (주가수익비율) (13.47배)
- eps: EPS (주당순이익) (4,950원)
- pbr: PBR (주가순자산비율) (1.15배)
- itewhol_loan_rmnd_ratem name: 대차잔고비율 (0.24%)
</details>

<details>
<summary>output2 | 일봉 히스토리 데이터</summary>

**날짜/가격 정보**
- stck_bsop_date: 주식 영업일자 (거래일, YYYYMMDD 형식)
- stck_clpr: 종가 (해당일 마감가)
- stck_oprc: 시가 (해당일 시작가)
- stck_hgpr: 고가 (해당일 최고가)
- stck_lwpr: 저가 (해당일 최저가)

**거래 정보**
- acml_vol: 누적 거래량 (해당일 총 거래주식수)
- acml_tr_pbmn: 누적 거래대금 (해당일 총 거래금액)

**등락 정보**
- prdy_vrss: 전일 대비 (전 거래일 대비 등락금액)
- prdy_vrss_sign: 전일 대비 부호 (2:상승, 5:하락, 3:보합)

**기타 정보**
- flng_cls_code: 락구분코드 (00:해당없음)
- prtt_rate: 분할비율 (액면분할 시 비율, 0.00:해당없음)
- mod_yn: 수정주가반영여부 (Y/N)
- revl_issu_reas: 재평가사유 (보통 공란)

</details>


### 어떤 데이터들을 얻어와야 함?
1. 특정 종목의 특정 시작일부터 특정 종료일까지 데이터 가쟈오기
<details>
<summary>CREON 예시</summary>

- code : 가져올 주식 종목의 코드
- date_from : 시작일
- date_to : 종료일

```python
def creon_7400_주식차트조회(self, code, date_from, date_to):
    b_connected = self.obj_CpCybos.IsConnec t
    if b_connected == 0:
        print("연결 실패")
        return None

    list_field_key = [0, 1, 2, 3, 4, 5, 8]
    list_field_name = ['date', 'time', 'open', 'high', 'low', 'close', 'volume']
    dict_chart = {name: [] for name in list_field_name}

    self.obj_StockChart.SetInputValue(0, 'A'+code)
    self.obj_StockChart.SetInputValue(1, ord('1'))  # 0: 개수, 1: 기간
    self.obj_StockChart.SetInputValue(2, date_to)  # 종료일
    self.obj_StockChart.SetInputValue(3, date_from)  # 시작일
    self.obj_StockChart.SetInputValue(5, list_field_key)  # 필드
    self.obj_StockChart.SetInputValue(6, ord('D'))  # 'D', 'W', 'M', 'm', 'T'
    self.obj_StockChart.BlockRequest()

    status = self.obj_StockChart.GetDibStatus()
    msg = self.obj_StockChart.GetDibMsg1()
    print("통신상태: {} {}".format(status, msg))
    if status != 0:
        return None

    cnt = self.obj_StockChart.GetHeaderValue(3)  # 수신개수
    for i in range(cnt):
        dict_item = (
            {name: self.obj_StockChart.GetDataValue(pos, i) 
            for pos, name in zip(range(len(list_field_name)), list_field_name)}
        )
        for k, v in dict_item.items():
            dict_chart[k].append(v)

    print("차트: {} {}".format(cnt, dict_chart))
    return pd.DataFrame(dict_chart, columns=list_field_name)
```
</details>