"""Quick verification script for admin setup"""
import os
import django
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.accounts.models import SubAdminProfile
from apps.subadmin.models import SubAdminPerformance
from apps.admin_dashboard.models import AdminDashboardSettings

User = get_user_model()

print("\n" + "="*60)
print("📊 MANTRA Admin/SubAdmin Setup Status")
print("="*60)

# Count records
admins_count = User.objects.filter(user_type='admin').count()
subadmins_count = User.objects.filter(user_type='subadmin').count()
profiles_count = SubAdminProfile.objects.count()
performance_count = SubAdminPerformance.objects.count()
settings_count = AdminDashboardSettings.objects.count()

print(f"\n👥 Users:")
print(f"  • Admins: {admins_count}")
print(f"  • SubAdmins: {subadmins_count}")

print(f"\n📁 Related Records:")
print(f"  • SubAdmin Profiles: {profiles_count}")
print(f"  • Performance Tracking: {performance_count}")
print(f"  • Admin Dashboard Settings: {settings_count}")

print(f"\n🔍 Admin Users:")
for admin in User.objects.filter(user_type='admin'):
    has_settings = AdminDashboardSettings.objects.filter(admin_user=admin).exists()
    status = "✅" if has_settings else "❌"
    print(f"  {status} {admin.username} ({admin.email})")

print(f"\n🔍 SubAdmin Users:")
for subadmin in User.objects.filter(user_type='subadmin'):
    has_profile = SubAdminProfile.objects.filter(user=subadmin).exists()
    has_perf = SubAdminPerformance.objects.filter(subadmin=subadmin).exists()
    status = "✅" if (has_profile and has_perf) else "❌"
    try:
        profile = SubAdminProfile.objects.get(user=subadmin)
        region_info = f" - {profile.region} {profile.assigned_areas}"
    except SubAdminProfile.DoesNotExist:
        region_info = " - No profile"
    print(f"  {status} {subadmin.username} ({subadmin.email}){region_info}")

print("\n" + "="*60)
print("✅ Verification Complete!")
print("="*60 + "\n")
