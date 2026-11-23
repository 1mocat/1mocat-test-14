#!/usr/bin/env python3
"""
Re-implementation of the COBOL BOOKFORUM program.
Reads INPUT.DAT and updates ACCOUNTS.DAT, BOOKS.DAT, TRANSACTIONS.DAT
with the same logic as the original COBOL.
"""

import os

# Paths relative to the cobol/ directory (as the COBOL is run from there)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SRC_DIR = os.path.join(BASE_DIR, "src")

INPUT_FILE = os.path.join(SRC_DIR, "INPUT.DAT")
ACCOUNTS_FILE = os.path.join(DATA_DIR, "ACCOUNTS.DAT")
BOOKS_FILE = os.path.join(DATA_DIR, "BOOKS.DAT")
TRANSACTIONS_FILE = os.path.join(DATA_DIR, "TRANSACTIONS.DAT")

# Record lengths (fixed)
ACCOUNT_LEN = 4 + 20 + 10  # 34
BOOK_LEN = 4 + 20 + 4      # 28
TRANS_LEN = 4 + 10 + 4 + 4 # 22
INPUT_LEN = 4 + 4 + 4 + 10 # 22


def pad_record(data: bytes, length: int) -> bytes:
    """Pad a short record with spaces to fixed length, as COBOL sequential does."""
    if len(data) < length:
        return data + b" " * (length - len(data))
    return data[:length]


def parse_numeric(field: bytes) -> int:
    """Parse a PIC 9(n) field, treating spaces as zeros (COBOL numeric conversion)."""
    s = field.decode("ascii", errors="replace").replace(" ", "0")
    return int(s) if s.isdigit() else 0


def read_fixed_records(path: str, record_len: int) -> list:
    """Read a sequential fixed-length file into a list of records (bytes)."""
    if not os.path.exists(path):
        return []
    with open(path, "rb") as f:
        data = f.read()
    records = []
    for i in range(0, len(data), record_len):
        rec = data[i:i + record_len]
        if rec:
            records.append(pad_record(rec, record_len))
    return records


def write_fixed_records(path: str, records: list, record_len: int):
    """Write list of fixed-length records back to file."""
    with open(path, "wb") as f:
        for rec in records:
            f.write(pad_record(rec, record_len))


def main():
    # Read input
    if not os.path.exists(INPUT_FILE):
        print("Error: Input file is empty")
        return

    with open(INPUT_FILE, "rb") as f:
        raw = f.read()
    if not raw:
        print("Error: Input file is empty")
        return

    input_rec = pad_record(raw, INPUT_LEN)
    buyer_id = input_rec[0:4].decode("ascii")
    seller_id = input_rec[4:8].decode("ascii")
    book_id = input_rec[8:12].decode("ascii")
    amount = parse_numeric(input_rec[12:22])

    # Validate users and book
    accounts = read_fixed_records(ACCOUNTS_FILE, ACCOUNT_LEN)
    buyer_found = False
    seller_found = False
    for rec in accounts:
        acc_id = rec[0:4].decode("ascii")
        if acc_id == buyer_id:
            buyer_found = True
        if acc_id == seller_id:
            seller_found = True

    books = read_fixed_records(BOOKS_FILE, BOOK_LEN)
    book_found = False
    valid_owner = False
    for rec in books:
        b_id = rec[0:4].decode("ascii")
        owner = rec[24:28].decode("ascii")
        if b_id == book_id:
            book_found = True
            if owner == seller_id:
                valid_owner = True

    print(" ")  # COBOL has DISPLAY " ".

    if buyer_found and seller_found and book_found and valid_owner:
        # Process transaction
        # Update accounts
        for i, rec in enumerate(accounts):
            acc_id = rec[0:4].decode("ascii")
            if acc_id == buyer_id or acc_id == seller_id:
                balance = parse_numeric(rec[24:34])
                if acc_id == buyer_id:
                    balance -= amount
                else:
                    balance += amount
                # Clamp or just format as 10 digits (COBOL PIC 9(10) wraps or errors, but for positive assume)
                bal_str = f"{max(0, balance):010d}"[:10]  # keep non-negative for safety
                new_rec = rec[:24] + bal_str.encode("ascii") + rec[34:]
                accounts[i] = new_rec

        write_fixed_records(ACCOUNTS_FILE, accounts, ACCOUNT_LEN)

        # Update book owner
        for i, rec in enumerate(books):
            b_id = rec[0:4].decode("ascii")
            if b_id == book_id:
                new_rec = rec[:24] + buyer_id.encode("ascii") + rec[28:]
                books[i] = new_rec
                break
        write_fixed_records(BOOKS_FILE, books, BOOK_LEN)

        # Append transaction
        # TRANS-BOOK X(4) + AMOUNT 9(10) + SELLER X(4) + BUYER X(4)
        # Note: in COBOL, MOVE WS-AMOUNT TO TRANS-AMOUNT, amount is integer part
        amt_str = f"{amount:010d}"
        trans_rec = (
            book_id.encode("ascii")
            + amt_str.encode("ascii")
            + seller_id.encode("ascii")
            + buyer_id.encode("ascii")
        )
        # OPEN EXTEND means append
        with open(TRANSACTIONS_FILE, "ab") as f:
            f.write(trans_rec)

        print("Transaction completed successfully")
    else:
        print("Transaction failed due to validation errors")


if __name__ == "__main__":
    main()
