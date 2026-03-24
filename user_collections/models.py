from django.db import models
from django.contrib.auth.models import User
from games.models import MTGCard, Pokemon, MTGSet

class UserMTGCollection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    card = models.ForeignKey(MTGCard, on_delete=models.CASCADE)
    collected = models.BooleanField(default=False)
    is_foil = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'card')

class UserPokemonCollection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE)
    collected = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'pokemon')

class Binder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class BinderSet(models.Model):
    binder = models.ForeignKey(Binder, on_delete=models.CASCADE, related_name='sets')
    mtg_set = models.ForeignKey(MTGSet, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('binder', 'mtg_set')

    def __str__(self):
        return f"{self.binder.name} - {self.mtg_set.name}"