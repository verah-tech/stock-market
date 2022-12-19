# app/worker.py

import finnhub
from celery import Celery
from app.db import pool
from app.settings import settings

client = finnhub.Client(api_key=settings.api_key)
celery_app = Celery(broker=settings.celery_broker)

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Set up a periodic task for every symbol defined in the settings.
    """
    for symbol in settings.symbols:
        sender.add_periodic_task(settings.frequency, fetch.s(symbol))


@celery_app.task
def fetch(symbol: str):
    """
    Fetch the stock info for a given symbol from Finnhub and load it into QuestDB.
    """

    quote: dict = client.quote(symbol)
    # https://finnhub.io/docs/api/quote
    # quote = {'c': 148.96, 'd': -0.84, 'dp': -0.5607, 'h': 149.7, 'l': 147.8, 'o': 148.985, 'pc': 149.8, 't': 1635796803}
    # c: Current price
    # d: Change
    # dp: Percent change
    # h: High price of the day
    # l: Low price of the day
    # o: Open price of the day
    # pc: Previous close price
    # t: when it was traded
    query = f"""
    INSERT INTO quotes(stock_symbol, current_price, high_price, low_price, open_price, percent_change, tradets, ts)
    VALUES(
        '{symbol}',
        {quote["c"]},
        {quote["h"]},
        {quote["l"]},
        {quote["o"]},
        {quote["pc"]},
        {quote["t"]} * 1000000,
        systimestamp()
    );
    """

    with pool.connection() as conn:
        conn.execute(query)
