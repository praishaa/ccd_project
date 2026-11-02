import os
import logging
import requests
import azure.functions as func

app = func.FunctionApp()


@app.timer_trigger(schedule="0 */5 * * * *", arg_name="timer", run_on_startup=False)
def low_stock_check(timer: func.TimerRequest) -> None:
    url = os.environ["API_BASE_URL"] + "/internal/low-stock-check"
    r = requests.post(url, headers={"x-api-key": os.environ["FUNC_API_KEY"]}, timeout=20)
    logging.info("low-stock check: status=%s body=%s", r.status_code, r.text)