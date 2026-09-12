from django.db import migrations, models
class Migration(migrations.Migration):
 dependencies=[("accounts","0005_historydocumentupload")]
 operations=[
  migrations.AddField(model_name="userprofile",name="founder_capital_band",field=models.CharField(blank=True,max_length=64)),
  migrations.AddField(model_name="userprofile",name="founder_context_scope",field=models.CharField(blank=True,max_length=32)),
  migrations.AddField(model_name="userprofile",name="founder_product_anchor_type",field=models.CharField(blank=True,max_length=64)),
  migrations.AddField(model_name="userprofile",name="founder_product_phase",field=models.CharField(blank=True,max_length=64)),
  migrations.AddField(model_name="userprofile",name="founder_team_band",field=models.CharField(blank=True,max_length=64)),
 ]