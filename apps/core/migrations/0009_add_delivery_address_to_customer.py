from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_add_user_onetoone_to_customer'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='delivery_address',
            field=models.TextField(blank=True, help_text='Delivery address', null=True),
        ),
    ]
