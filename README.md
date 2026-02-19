# RausgegangenLotteryBot

Lottery Bot for the german event page "Rausgegangen.de". Supports multiple accounts and uses Selenium. Needs to have firefox installed.

Currently defaults to Stuttgart. Could be changed in the future.

## Usage:
Create .env file in this format:
```
# .env file
ACCOUNT_1_EMAIL=
ACCOUNT_1_PASSWORD=

ACCOUNT_2_EMAIL=
ACCOUNT_2_PASSWORD=
```
Currently only exactly 2 accounts are supported. If more or less than 2 accounts, change manually in Python file.
Then run RausgegangenLotteryBot.py

