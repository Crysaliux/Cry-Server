from datetime import datetime, date, timedelta

bdate = date.fromisoformat('2012-03-04')

delta = date.today() - bdate
if divmod(delta.total_seconds(), 31536000)[0] < 13: print('nope')
else: print('dope')