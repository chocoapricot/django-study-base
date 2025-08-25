from django.contrib import admin
from .models import StaffProfile, StaffProfileQualification, StaffProfileSkill, ProfileMynumber, StaffProfileInternational

admin.site.register(StaffProfile)
admin.site.register(StaffProfileQualification)
admin.site.register(StaffProfileSkill)
admin.site.register(ProfileMynumber)
admin.site.register(StaffProfileInternational)
