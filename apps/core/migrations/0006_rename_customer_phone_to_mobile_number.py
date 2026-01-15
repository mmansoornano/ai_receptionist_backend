# Generated migration to rename customer_phone to mobile_number
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_activitylog'),
    ]

    operations = [
        migrations.RunSQL(
            # SQLite doesn't support ALTER TABLE RENAME COLUMN directly, so we need to recreate the table
            sql="""
            CREATE TABLE core_payment_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mobile_number varchar(20) NOT NULL,
                payment_method varchar(20) NOT NULL,
                otp_code varchar(6) NULL,
                otp_verified bool NOT NULL,
                otp_expires_at datetime NULL,
                amount decimal NOT NULL,
                status varchar(20) NOT NULL,
                transaction_id varchar(255) NULL,
                created_at datetime NOT NULL,
                updated_at datetime NOT NULL,
                order_id bigint NULL REFERENCES core_order(id)
            );
            INSERT INTO core_payment_new (id, mobile_number, payment_method, otp_code, otp_verified, otp_expires_at, amount, status, transaction_id, created_at, updated_at, order_id)
            SELECT id, customer_phone, payment_method, otp_code, otp_verified, otp_expires_at, amount, status, transaction_id, created_at, updated_at, order_id
            FROM core_payment;
            DROP TABLE core_payment;
            ALTER TABLE core_payment_new RENAME TO core_payment;
            """,
            reverse_sql="""
            CREATE TABLE core_payment_old (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_phone varchar(20) NOT NULL,
                payment_method varchar(20) NOT NULL,
                otp_code varchar(6) NULL,
                otp_verified bool NOT NULL,
                otp_expires_at datetime NULL,
                amount decimal NOT NULL,
                status varchar(20) NOT NULL,
                transaction_id varchar(255) NULL,
                created_at datetime NOT NULL,
                updated_at datetime NOT NULL,
                order_id bigint NULL REFERENCES core_order(id)
            );
            INSERT INTO core_payment_old (id, customer_phone, payment_method, otp_code, otp_verified, otp_expires_at, amount, status, transaction_id, created_at, updated_at, order_id)
            SELECT id, mobile_number, payment_method, otp_code, otp_verified, otp_expires_at, amount, status, transaction_id, created_at, updated_at, order_id
            FROM core_payment;
            DROP TABLE core_payment;
            ALTER TABLE core_payment_old RENAME TO core_payment;
            """
        ),
    ]
