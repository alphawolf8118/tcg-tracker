from django.db import models

class MTGSet(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=10)
    release_date = models.DateField()
    card_count = models.IntegerField()
    digital = models.BooleanField(default=False)  # New field to track digital sets
    symbol_url = models.URLField(blank=True, help_text="URL to the set symbol image")  # New field

    class Meta:
        ordering = ['-release_date']  # Newest first

    def __str__(self):
        return f"{self.name} ({self.code})"

class MTGCard(models.Model):
    set = models.ForeignKey(MTGSet, on_delete=models.CASCADE, related_name='cards')
    name = models.CharField(max_length=255)
    image_url = models.URLField(blank=True)
    collector_number = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.name} ({self.collector_number})"

class Pokemon(models.Model):
    dex_number = models.PositiveIntegerField(unique=True)  # National dex number (1-1025)
    name = models.CharField(max_length=255)
    image_url = models.URLField(blank=True)

    class Meta:
        ordering = ['dex_number']  # Ordered by dex number (1-1025)

    def __str__(self):
        return f"#{self.dex_number} {self.name}"