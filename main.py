import time
import eel
import module.token_manager as token_manager
import module.stock_data_manager as stock_data_manager

# INVEST_TYPE = "PROD"  # 실전투자
INVEST_TYPE = "VPS"    # 모의투자

if __name__ == "__main__":
    # keys = token_manager.get_keys()

    test_data = stock_data_manager.get_itempricechart_1(
        div_code="J", 
        itm_no="005930",  # 삼성전자
        start_date=20250701, 
        end_date=20250715, 
        period_code="D", 
        adj_prc="1",
    )

    print(test_data)
    print("\n\n----\n\n")

    test_data = stock_data_manager.get_itempricechart_2(
        div_code="J", 
        itm_no="005930",  # 삼성전자
        start_date=20250701, 
        end_date=20250715, 
        period_code="D", 
        adj_prc="1"
    )

    print(test_data)
    print("\n\n----\n\n")

    # sleep
    time.sleep(1)

    test_data = stock_data_manager.get_daily_price(
        div_code="J", 
        itm_no="005930",  # 삼성전자
        period_code="D", 
        adj_prc_code="1",
    )

    print(test_data)

    # eel.init("web")
    # eel.start("web/index.html", size=(800, 600))