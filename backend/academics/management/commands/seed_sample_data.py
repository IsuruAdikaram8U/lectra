"""
Management command to seed rich, multi-batch/multi-degree sample data into Lectra.

Builds cleanly and idempotently on top of `seed_it_timetable` using real data
from the Faculty of Information Technology timetable PDFs in `docs/`:
  - Departments: CM, IT, IDS, NT
  - DegreePrograms: IT, AI, ITM
  - Batches: B22 (Sem 7), B23 (Sem 5), B24 (Sem 3), B25 (Sem 1) + BatchDegreeEnrollments
  - Modules & ModuleDegreeMappings for B23 AI, B23 ITM, and B24 IT
  - Additional Lecturers + Lecturer specializations + LecturerAvailability windows
  - Extra Halls (ensuring any referenced halls exist) & StudentGroups
  - PUBLISHED Timetables + ScheduleEntries for B23 IT, B23 AI, B23 ITM, and B24 IT
  - Extra test Users across roles (ADMIN, HOD, STUDENT)

Usage:
    python manage.py seed_sample_data

NOTE: Seeded test accounts use placeholder password 'Lectra@2026' for local
development/testing only — never use these credentials in production.
"""

from datetime import date, time

from django.core.management.base import BaseCommand
from django.db import transaction

from academics.models import (
    Batch,
    BatchDegreeEnrollment,
    DegreeProgram,
    Department,
    GroupBatchMapping,
    Hall,
    HallType,
    Lecturer,
    LecturerAvailability,
    Module,
    ModuleDegreeMapping,
    ModuleLecturer,
    StudentGroup,
)
from accounts.models import Tenant, User
from scheduling.models import ScheduleEntry, Timetable


class Command(BaseCommand):
    help = "Seed rich multi-batch, multi-degree sample data into Lectra."

    def handle(self, *args, **options):
        with transaction.atomic():
            tenant = self._get_or_create_tenant()
            departments = self._seed_departments(tenant)
            degrees = self._seed_degree_programs(tenant, departments)
            batches = self._seed_batches(tenant)
            self._seed_batch_enrollments(batches, degrees)
            halls = self._seed_halls(tenant)
            lecturers = self._seed_lecturers(tenant, departments)
            self._seed_lecturer_availability(lecturers)
            modules = self._seed_modules(tenant, departments)
            self._seed_module_degree_mappings(modules, degrees)
            self._seed_module_lecturers(modules, lecturers)
            groups = self._seed_student_groups(tenant, batches)
            self._seed_timetables_and_entries(
                tenant, batches, degrees, modules, lecturers, halls, groups
            )
            self._seed_test_users(tenant)

        self.stdout.write(
            self.style.SUCCESS("\nSample data seeding complete (idempotent).")
        )

    # ------------------------------------------------------------------
    # 1. Tenant & Departments
    # ------------------------------------------------------------------
    def _get_or_create_tenant(self):
        tenant, _ = Tenant.objects.get_or_create(
            name="Faculty of Information Technology",
            defaults={"domain_prefix": "fit"},
        )
        return tenant

    def _seed_departments(self, tenant):
        dept_rows = [
            ("CM", "Computer Systems / CM Department"),
            ("IT", "Information Technology"),
            ("IDS", "Interdisciplinary Studies"),
            ("NT", "Non-Technical & General Studies"),
        ]
        departments = {}
        for code, name in dept_rows:
            dept, _ = Department.objects.get_or_create(
                tenant=tenant, code=code, defaults={"name": name}
            )
            departments[code] = dept
        self.stdout.write(f"Departments ready: {len(departments)}")
        return departments

    # ------------------------------------------------------------------
    # 2. Degree Programs & Batches
    # ------------------------------------------------------------------
    def _seed_degree_programs(self, tenant, departments):
        degree_rows = [
            ("IT", "Information Technology", "IT"),
            ("AI", "Artificial Intelligence", "CM"),
            ("ITM", "Information Technology & Management", "IDS"),
        ]
        degrees = {}
        for code, name, dept_code in degree_rows:
            degree, _ = DegreeProgram.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={"department": departments[dept_code], "name": name},
            )
            degrees[code] = degree
        self.stdout.write(f"DegreePrograms ready: {len(degrees)}")
        return degrees

    def _seed_batches(self, tenant):
        batch_rows = [
            ("B22", 7),
            ("B23", 5),
            ("B24", 3),
            ("B25", 1),
        ]
        batches = {}
        for name, sem in batch_rows:
            batch, _ = Batch.objects.get_or_create(
                tenant=tenant, name=name, defaults={"current_semester": sem}
            )
            batches[name] = batch
        self.stdout.write(f"Batches ready: {len(batches)}")
        return batches

    def _seed_batch_enrollments(self, batches, degrees):
        enrollment_rows = [
            ("B22", "IT", 240),
            ("B22", "AI", 55),
            ("B22", "ITM", 120),
            ("B23", "IT", 250),
            ("B23", "AI", 60),
            ("B23", "ITM", 125),
            ("B24", "IT", 260),
            ("B24", "AI", 65),
            ("B24", "ITM", 130),
            ("B25", "IT", 270),
            ("B25", "AI", 70),
            ("B25", "ITM", 135),
        ]
        for batch_name, deg_code, count in enrollment_rows:
            BatchDegreeEnrollment.objects.get_or_create(
                batch=batches[batch_name],
                degree_program=degrees[deg_code],
                defaults={"student_count": count},
            )
        self.stdout.write(f"BatchDegreeEnrollments ready: {len(enrollment_rows)}")

    # ------------------------------------------------------------------
    # 3. Halls
    # ------------------------------------------------------------------
    def _seed_halls(self, tenant):
        hall_rows = [
            ("1LH01A", "Lecture Hall 1LH01A", HallType.LECTURE_HALL, 80, 80, True),
            ("1LH02A", "Lecture Hall 1LH02A", HallType.LECTURE_HALL, 80, 80, True),
            ("1LH03A", "Lecture Hall 1LH03A", HallType.LECTURE_HALL, 80, 80, True),
            ("2LH01A", "Lecture Hall 2LH01A", HallType.LECTURE_HALL, 80, 80, True),
            ("2LH02A", "Lecture Hall 2LH02A", HallType.LECTURE_HALL, 80, 80, True),
            ("2LH03A", "Lecture Hall 2LH03A", HallType.LECTURE_HALL, 80, 80, True),
            ("3LH01A", "Lecture Hall 3LH01A", HallType.LECTURE_HALL, 80, 80, True),
            ("3LH02A", "Lecture Hall 3LH02A", HallType.LECTURE_HALL, 80, 80, True),
            ("4DL01", "Lecture Hall 4DL01", HallType.LECTURE_HALL, 60, 60, True),
            ("4LH01A", "Lecture Hall 4LH01A", HallType.LECTURE_HALL, 80, 80, True),
            ("4LH02A", "Lecture Hall 4LH02A", HallType.LECTURE_HALL, 80, 80, True),
            ("0LH01A", "Lecture Hall 0LH01A", HallType.LECTURE_HALL, 80, 80, True),
            ("0LH02A", "Lecture Hall 0LH02A", HallType.LECTURE_HALL, 80, 80, True),
            ("LAB1", "Computer Lab 1", HallType.COMPUTER_LAB, 40, 35, False),
            ("LAB2", "Computer Lab 2", HallType.COMPUTER_LAB, 40, 35, False),
            ("LAB3", "Computer Lab 3", HallType.COMPUTER_LAB, 40, 35, False),
            ("LAB4", "Computer Lab 4", HallType.COMPUTER_LAB, 40, 35, False),
            ("LAB5", "Computer Lab 5", HallType.COMPUTER_LAB, 40, 35, False),
            ("LAB6", "Computer Lab 6", HallType.COMPUTER_LAB, 40, 35, False),
            ("LAB7", "Computer Lab 7", HallType.COMPUTER_LAB, 40, 35, False),
            ("LAB8", "Computer Lab 8", HallType.COMPUTER_LAB, 40, 35, False),
            ("AILAB", "AI Lab", HallType.COMPUTER_LAB, 30, 25, False),
            ("LAB30B", "Lab 30B", HallType.COMPUTER_LAB, 30, 30, False),
            ("HPCLAB", "HPC Lab", HallType.COMPUTER_LAB, 25, 25, False),
            ("MACLAB", "MAC Lab", HallType.COMPUTER_LAB, 25, 25, False),
            ("NETLAB", "Network Lab", HallType.COMPUTER_LAB, 25, 25, False),
            ("HWLAB1", "Hardware Lab 1", HallType.HARDWARE_LAB, 25, 25, False),
            ("HWLAB2", "Hardware Lab 2", HallType.HARDWARE_LAB, 25, 25, False),
            ("ERPLAB", "ERP System Lab", HallType.COMPUTER_LAB, 30, 30, False),
            ("EMBLAB", "Electronic & Embedded System Lab", HallType.HARDWARE_LAB, 25, 25, False),
            ("BEHLAB", "Behavioral Science Lab", HallType.COMPUTER_LAB, 25, 25, False),
            ("DSLAB", "Data Science Lab", HallType.COMPUTER_LAB, 30, 30, False),
        ]
        halls = {}
        for code, name, hall_type, total_cap, usable_cap, projector in hall_rows:
            hall, _ = Hall.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={
                    "name": name,
                    "hall_type": hall_type,
                    "total_capacity": total_cap,
                    "usable_capacity": usable_cap,
                    "has_projector": projector,
                },
            )
            halls[code] = hall
        return halls

    # ------------------------------------------------------------------
    # 4. Lecturers & Availability
    # ------------------------------------------------------------------
    def _seed_lecturers(self, tenant, departments):
        # Includes existing lecturers (to enrich specialization) + new ones from AI/ITM/B24 PDFs.
        lecturer_rows = [
            # Existing from seed_it_timetable
            ("piyatilake_its", "Dr.(Ms)", "Piyatilake I.T.S", "CM", "Numerical Methods & Cognitive Systems"),
            ("silva_atp", "Prof.(Mrs)", "Silva A.T.P.", "CM", "Machine Learning & Automata Theory"),
            ("karunananda_as", "Prof.", "Karunananda A.S.", "CM", "Artificial Intelligence & Multi-Agent Systems"),
            ("premadasa_mgnn", "Ms.", "Premadasa M.G.N.N.", "IT", "Enterprise Application Development"),
            ("amalraj_crj", "Dr.", "Amalraj C.R.J.", "IT", "Distributed Systems & Computer Networks"),
            ("perera_yg", "Mr.", "Perera Y.G.", "IT", "Enterprise Systems"),
            ("nilnuwani_wag", "Ms.", "Nilnuwani W.A.G", "IT", "Network Programming"),
            ("githmi_ph", "Ms.", "Githmi P.H.", "IT", "Human Computer Interaction & Networking"),
            ("kumari_hkbk", "Ms.", "Kumari H.K.B.K", "IT", "Wireless Networks"),
            ("chandimali_mn", "Ms.", "Chandimali M.N.", "IT", "Mobile Application Development & Software Engineering"),
            ("rathnayake_rmdp", "Ms.", "Rathnayake R.M.D.P.", "IT", "Mobile & Interactive Systems"),
            ("sudantha_bh", "Mr.", "Sudantha B.H.", "IT", "Embedded Systems & IoT"),
            ("ranawaka_radpm", "Mr.", "Ranawaka R.A.D.P.M.", "IT", "Computer Architecture & Embedded Systems"),
            ("karunarathne_gti", "Mrs.", "Karunarathne G.T.I.", "IT", "Human Computer Interaction & Software Projects"),
            ("wijetunge_wasn", "Ms.", "Wijetunge W.A.S.N.", "IDS", "Communication Skills & IT Project Management"),
            ("ganegoda_gu", "Dr.(Ms)", "Ganegoda G.U.", "IDS", "Management Information Systems & Behavioural Genetics"),
            # Additional lecturers from B23 AI, B23 ITM, and B24 IT PDFs
            ("thanuja_alarr", "Dr.", "Thanuja A.L.A.R.R.", "CM", "Computational Statistics"),
            ("ranasinghe_ddm", "Dr.(Ms)", "Ranasinghe D.D.M.", "CM", "Artificial Cognitive Systems"),
            ("fernando_ksd", "Prof.(Ms)", "Fernando K.S.D.", "CM", "Neural Networks & Fuzzy Logic"),
            ("pirapaharan_a", "Ms.", "Pirapaharan A.", "IT", "Computer Architecture"),
            ("perera_man", "Ms.", "Perera M.A.N.", "IDS", "IT Project Management & Strategic Management"),
            ("karunaratne_pm", "Mr.", "Karunaratne P.M.", "IDS", "IT Project Management"),
            ("andrahennadi_s", "Mr.", "Andrahennadi S.", "IDS", "Project Management"),
            ("premaratne_sc", "Dr.", "Premaratne S.C.", "IT", "Operating Systems"),
            ("firdhous_mfm", "Dr.", "Firdhous M.F.M.", "IT", "Data Communication & Computer Networks"),
            ("sandanayake_tc", "Prof.(Mrs)", "Sandanayake T.C.", "IDS", "Organizational Behaviour"),
            ("fernando_dnn", "Ms.", "Fernando D.N.N.", "IDS", "Management & Organizational Studies"),
            ("seneviratne_bld", "Dr.", "Seneviratne B.L.D.", "IDS", "Strategic & Digital Business Management"),
            ("upeksha_pgs", "Ms.", "Upeksha P.G.S.", "IDS", "Digital Business Management"),
            ("hettiarachchi_dnm", "Ms.", "Hettiarachchi D.N.M.", "IDS", "Digital Business Management"),
            ("harshani_wgl", "Ms.", "Harshani W.G.L.", "IDS", "Management Information Systems"),
            ("thanthriwatta_tm", "Dr.", "Thanthriwatta T.M.", "IT", "Object Oriented Programming"),
            ("jayathilake_pkkns", "Mr.", "Jayathilake P.K.K.N.S.", "IT", "Object Oriented Programming"),
            ("ahangama_s", "Prof.(Ms)", "Ahangama S.", "IT", "Object-Oriented Analysis and Design"),
            ("ranathunga_l", "Dr.", "Ranathunga L.", "IT", "Computer Architecture & Multimedia"),
            ("maduwanthi_dmsk", "Ms.", "Maduwanthi D.M.S.K.", "CM", "Mathematical Methods"),
            ("nanayakkara_akb", "Ms.", "Nanayakkara A.K.B.", "IT", "Software Engineering"),
            ("udalamaththa_s", "Ms.", "Udalamaththa S.", "NT", "Ecology & Landscape Design"),
            ("dulanjana_ws", "Mr.", "Dulanjana W.S.", "NT", "Active Citizens"),
            ("wickramathilake_ba", "Dr.(Ms)", "Wickramathilake B.A.", "NT", "Health and Safety"),
            ("ranathunga_t", "Dr.(Ms)", "Ranathunga T.", "NT", "Human Nutrition"),
        ]

        lecturers = {}
        for username, title, full_name, dept_code, specialization in lecturer_rows:
            uom_email = f"{username}@uom.lk"
            user, created = User.objects.get_or_create(
                uom_email=uom_email,
                defaults={
                    "username": username,
                    "tenant": tenant,
                    "role": User.Role.LECTURER,
                    "email": uom_email,
                    "is_uom_verified": True,
                },
            )
            if created:
                user.set_password("Lectra@2026")
                user.save()

            lecturer, _ = Lecturer.objects.get_or_create(
                user=user,
                defaults={
                    "tenant": tenant,
                    "department": departments[dept_code],
                    "title": title,
                    "name": full_name,
                    "specialization": specialization,
                },
            )
            if not lecturer.specialization and specialization:
                lecturer.specialization = specialization
                lecturer.save(update_fields=["specialization"])
            lecturers[username] = lecturer

        self.stdout.write(f"Lecturers ready: {len(lecturers)}")
        return lecturers

    def _seed_lecturer_availability(self, lecturers):
        # Mix of available (True) and explicitly blocked (False) windows for testing
        availability_rows = [
            ("karunananda_as", "MONDAY", time(8, 15), time(12, 30), False),
            ("karunananda_as", "TUESDAY", time(13, 15), time(17, 30), True),
            ("karunananda_as", "WEDNESDAY", time(13, 15), time(17, 30), True),
            ("silva_atp", "MONDAY", time(13, 15), time(17, 30), True),
            ("silva_atp", "TUESDAY", time(8, 15), time(12, 30), False),
            ("silva_atp", "FRIDAY", time(8, 15), time(13, 0), True),
            ("amalraj_crj", "TUESDAY", time(8, 15), time(12, 30), False),
            ("amalraj_crj", "WEDNESDAY", time(10, 30), time(16, 30), True),
            ("amalraj_crj", "FRIDAY", time(8, 15), time(17, 30), True),
            ("piyatilake_its", "TUESDAY", time(10, 30), time(16, 30), True),
            ("piyatilake_its", "THURSDAY", time(8, 15), time(12, 30), True),
            ("premaratne_sc", "MONDAY", time(8, 15), time(12, 30), True),
            ("premaratne_sc", "THURSDAY", time(13, 15), time(17, 30), False),
            ("premaratne_sc", "FRIDAY", time(8, 15), time(12, 30), True),
            ("sudantha_bh", "TUESDAY", time(13, 15), time(17, 30), True),
            ("sudantha_bh", "WEDNESDAY", time(8, 15), time(12, 30), False),
            ("ganegoda_gu", "MONDAY", time(8, 15), time(12, 30), True),
            ("ganegoda_gu", "THURSDAY", time(13, 15), time(17, 30), False),
        ]
        for username, day, start, end, is_avail in availability_rows:
            LecturerAvailability.objects.get_or_create(
                lecturer=lecturers[username],
                day_of_week=day,
                start_time=start,
                end_time=end,
                defaults={"is_available": is_avail},
            )
        self.stdout.write(f"LecturerAvailability windows ready: {len(availability_rows)}")

    # ------------------------------------------------------------------
    # 5. Modules & Mappings
    # ------------------------------------------------------------------
    def _seed_modules(self, tenant, departments):
        # (code, title, dept_code, credits, semester, is_practical, hall_type)
        module_rows = [
            # B23 IT (already seeded by seed_it_timetable, kept here for lookup safety)
            ("CM3131", "Applied Numerical Methods", "CM", "2.50", 5, False, None),
            ("CM3211", "Automata Theory", "CM", "2.50", 5, False, None),
            ("CM3311", "Artificial Intelligence", "CM", "2.50", 5, False, None),
            ("IN3101", "Enterprise Application Development", "IT", "2.50", 5, True, HallType.COMPUTER_LAB),
            ("IN3111", "Network Programming", "IT", "2.50", 5, True, HallType.COMPUTER_LAB),
            ("IN3210", "Mobile Applications Development", "IT", "2.50", 5, True, HallType.COMPUTER_LAB),
            ("IN3320", "Embedded Systems", "IT", "2.50", 5, True, HallType.HARDWARE_LAB),
            ("IN3510", "Wireless Communication & Mobile Networks", "IT", "2.50", 5, False, None),
            ("IN3700", "Human Computer Interaction", "IT", "2.50", 5, False, None),
            ("IS3011", "Communication Skills and Professional Conduct", "IDS", "2.50", 5, False, None),
            ("IS3610", "Management Information Systems", "IDS", "2.50", 5, False, None),
            # B23 AI (Semester 5 / L3S1)
            ("CM3230", "Automata Theory (AI)", "CM", "2.50", 5, False, None),
            ("CM3430", "Computational Statistics", "CM", "2.50", 5, False, None),
            ("CM3610", "Expert Systems", "CM", "2.50", 5, False, None),
            ("CM3630", "Multi Agent System", "CM", "2.50", 5, False, None),
            ("CM3640", "Artificial Cognitive Systems", "CM", "2.50", 5, False, None),
            ("CM3710", "Artificial Neural Networks", "CM", "2.50", 5, True, HallType.COMPUTER_LAB),
            ("CM3720", "Machine Learning", "CM", "2.50", 5, True, HallType.COMPUTER_LAB),
            ("CM3810", "Fuzzy Logic", "CM", "2.50", 5, False, None),
            ("IN2321", "Computer Architecture", "IT", "2.50", 3, False, None),
            ("IS3700", "IT Project Management", "IDS", "2.50", 5, False, None),
            # B23 ITM (Semester 5)
            ("IN3311", "Operating Systems", "IT", "2.50", 5, True, HallType.COMPUTER_LAB),
            ("IN3530", "Data Communication & Computer Networks", "IT", "2.50", 5, False, None),
            ("IS3020", "Human Communication and Language Structures", "IDS", "2.50", 5, False, None),
            ("IS3120", "Organizational Behaviour", "IDS", "2.50", 5, False, None),
            ("IS3130", "Strategic Management", "IDS", "2.50", 5, False, None),
            ("IS3200", "Digital Business Management", "IDS", "2.50", 5, False, None),
            ("IS3510", "Fundamentals of Behavioural Genetics", "IDS", "2.50", 5, False, None),
            ("IS3520", "Fundamentals of Behavioural Science", "IDS", "2.50", 5, False, None),
            ("IS3920", "Individual Project on Business Solutions", "IDS", "2.50", 5, False, None),
            # B24 IT (Semester 3)
            ("CM2131", "Essentials of Mathematical Methods", "CM", "2.50", 3, False, None),
            ("IN2101", "Object Oriented Programming", "IT", "3.00", 3, True, HallType.COMPUTER_LAB),
            ("IN2201", "Software Engineering", "IT", "3.00", 3, True, HallType.COMPUTER_LAB),
            ("IN2211", "Object-Oriented Analysis and Design", "IT", "2.50", 3, True, HallType.COMPUTER_LAB),
            ("IN2311", "Operating System", "IT", "2.50", 3, True, HallType.COMPUTER_LAB),
            ("IN2901", "Software Development Project", "IT", "4.00", 3, True, HallType.COMPUTER_LAB),
            ("DI1001", "Health and Safety", "NT", "2.00", 3, False, None),
            ("DI1013", "Appreciation of Literary Works", "NT", "2.00", 3, False, None),
            ("DI1015", "Counselling", "NT", "2.00", 3, False, None),
            ("DI1016", "Introduction to Ecology and Landscape Design", "NT", "2.00", 3, False, None),
            ("DI1017", "Active Citizens", "NT", "2.00", 3, False, None),
            ("DI1018", "Fundamentals of Human Nutrition", "NT", "2.00", 3, False, None),
        ]

        modules = {}
        for code, title, dept_code, credits, sem, is_prac, hall_type in module_rows:
            module, _ = Module.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={
                    "department": departments[dept_code],
                    "title": title,
                    "credits": credits,
                    "semester": sem,
                    "is_practical": is_prac,
                    "required_hall_type": hall_type,
                },
            )
            modules[code] = module
        self.stdout.write(f"Modules ready: {len(modules)}")
        return modules

    def _seed_module_degree_mappings(self, modules, degrees):
        degree_modules = {
            "IT": [
                "CM3131", "CM3211", "CM3311", "IN3101", "IN3111", "IN3210",
                "IN3320", "IN3510", "IN3700", "IS3011", "IS3610",
                "CM2131", "IN2101", "IN2201", "IN2211", "IN2311", "IN2321",
                "IN2901", "DI1001", "DI1013", "DI1015", "DI1016", "DI1017", "DI1018",
            ],
            "AI": [
                "CM3230", "CM3430", "CM3610", "CM3630", "CM3640", "CM3710",
                "CM3720", "CM3810", "IN2321", "IN3101", "IS3700",
            ],
            "ITM": [
                "CM3211", "CM3311", "IN3101", "IN3210", "IN3311", "IN3320",
                "IN3530", "IN3700", "IS3011", "IS3020", "IS3120", "IS3130",
                "IS3200", "IS3510", "IS3520", "IS3610", "IS3700", "IS3920",
            ],
        }
        count = 0
        for deg_code, mod_codes in degree_modules.items():
            for mod_code in mod_codes:
                ModuleDegreeMapping.objects.get_or_create(
                    module=modules[mod_code], degree_program=degrees[deg_code]
                )
                count += 1
        self.stdout.write(f"ModuleDegreeMappings ready: {count}")

    def _seed_module_lecturers(self, modules, lecturers):
        assignments = {
            "CM3230": ["silva_atp"],
            "CM3430": ["thanuja_alarr"],
            "CM3610": ["karunananda_as"],
            "CM3630": ["karunananda_as"],
            "CM3640": ["piyatilake_its", "ranasinghe_ddm"],
            "CM3710": ["fernando_ksd"],
            "CM3720": ["silva_atp"],
            "CM3810": ["fernando_ksd"],
            "IN2321": ["ranawaka_radpm", "amalraj_crj", "pirapaharan_a", "ranathunga_l"],
            "IS3700": ["perera_man", "wijetunge_wasn", "karunaratne_pm", "andrahennadi_s"],
            "IN3311": ["premaratne_sc"],
            "IN3530": ["firdhous_mfm"],
            "IS3020": ["wijetunge_wasn"],
            "IS3120": ["perera_man", "sandanayake_tc", "fernando_dnn"],
            "IS3130": ["seneviratne_bld", "perera_man", "fernando_dnn"],
            "IS3200": ["upeksha_pgs", "seneviratne_bld", "hettiarachchi_dnm"],
            "IS3510": ["ganegoda_gu"],
            "IS3520": ["seneviratne_bld"],
            "IS3920": ["seneviratne_bld"],
            "CM2131": ["piyatilake_its", "maduwanthi_dmsk"],
            "IN2101": ["thanthriwatta_tm", "jayathilake_pkkns"],
            "IN2201": ["amalraj_crj", "chandimali_mn", "nanayakkara_akb"],
            "IN2211": ["ahangama_s", "premadasa_mgnn"],
            "IN2311": ["premaratne_sc", "ranawaka_radpm"],
            "IN2901": ["karunarathne_gti"],
            "DI1001": ["wickramathilake_ba", "wijetunge_wasn", "fernando_dnn"],
            "DI1013": ["wijetunge_wasn"],
            "DI1015": ["wijetunge_wasn", "perera_man"],
            "DI1016": ["udalamaththa_s", "fernando_dnn"],
            "DI1017": ["sandanayake_tc", "dulanjana_ws", "upeksha_pgs"],
            "DI1018": ["ranathunga_t", "wijetunge_wasn", "perera_man"],
        }
        count = 0
        for mod_code, usernames in assignments.items():
            for username in usernames:
                ModuleLecturer.objects.get_or_create(
                    module=modules[mod_code], lecturer=lecturers[username]
                )
                count += 1
        self.stdout.write(f"ModuleLecturers ready: {count}")

    # ------------------------------------------------------------------
    # 6. Student Groups
    # ------------------------------------------------------------------
    def _seed_student_groups(self, tenant, batches):
        group_specs = [
            ("IT-B23-Full", "B23", 250),
            ("AI-B23-Full", "B23", 60),
            ("ITM-B23-Full", "B23", 125),
            ("ITM-IS3011-G1", "B23", 42),
            ("ITM-IS3011-G2", "B23", 42),
            ("ITM-IS3011-G3", "B23", 41),
            ("IT-B24-Full", "B24", 260),
        ]
        groups = {}
        for name, batch_name, count in group_specs:
            group, _ = StudentGroup.objects.get_or_create(
                tenant=tenant, name=name, defaults={"total_students": count}
            )
            GroupBatchMapping.objects.get_or_create(
                student_group=group, batch=batches[batch_name], defaults={"student_count": count}
            )
            groups[name] = group
        self.stdout.write(f"StudentGroups ready: {len(groups)}")
        return groups

    # ------------------------------------------------------------------
    # 7. Timetables & Schedule Entries
    # ------------------------------------------------------------------
    def _seed_timetables_and_entries(
        self, tenant, batches, degrees, modules, lecturers, halls, groups
    ):
        # 7A. Publish a V1 Timetable for B23 IT (copying/aligning with real B23 IT schedule)
        b23_it_pub, _ = Timetable.objects.get_or_create(
            tenant=tenant,
            batch=batches["B23"],
            degree_program=degrees["IT"],
            status=Timetable.Status.PUBLISHED,
            defaults={
                "name": "B23 IT Semester 05 - Official V1",
                "valid_from": date(2026, 8, 31),
                "valid_to": date(2026, 12, 13),
            },
        )
        b23_it_entries = [
            ("MONDAY", "08:15", "09:15", "IS3610", "0LH01A", "ganegoda_gu", "IT-B23-Full", False, "LECTURE"),
            ("MONDAY", "15:30", "16:30", "CM3211", None, "silva_atp", "IT-B23-Full", True, "LECTURE"),
            ("TUESDAY", "13:15", "14:15", "CM3131", "1LH01A", "piyatilake_its", "IT-B23-Full", False, "LECTURE"),
            ("TUESDAY", "15:30", "16:30", "IN3320", "HWLAB1", "sudantha_bh", "IT-B23-Full", False, "LAB"),
            ("WEDNESDAY", "13:15", "14:15", "IN3210", "LAB4", "chandimali_mn", "IT-B23-Full", False, "LAB"),
            ("WEDNESDAY", "15:30", "16:30", "CM3311", "2LH01A", "karunananda_as", "IT-B23-Full", False, "LECTURE"),
            ("THURSDAY", "10:30", "11:30", None, "0LH01A", None, "IT-B23-Full", False, "LECTURE"),
            ("THURSDAY", "11:30", "12:30", None, "0LH01A", None, "IT-B23-Full", False, "LECTURE"),
            ("THURSDAY", "13:15", "14:15", "IN3700", "3LH01A", "karunarathne_gti", "IT-B23-Full", False, "LECTURE"),
            ("FRIDAY", "08:15", "09:15", "IN3111", "LAB5", "nilnuwani_wag", "IT-B23-Full", False, "LAB"),
            ("FRIDAY", "10:30", "11:30", "IN3510", "3LH02A", "amalraj_crj", "IT-B23-Full", False, "LECTURE"),
            ("FRIDAY", "16:30", "17:30", "IN3101", "LAB6", "premadasa_mgnn", "IT-B23-Full", False, "LAB"),
        ]
        self._populate_entries_if_empty(
            tenant, b23_it_pub, b23_it_entries, modules, lecturers, halls, groups
        )

        # 7B. Published Timetable for B23 AI (from B23 - AI Timetable.pdf)
        b23_ai_pub, _ = Timetable.objects.get_or_create(
            tenant=tenant,
            batch=batches["B23"],
            degree_program=degrees["AI"],
            status=Timetable.Status.PUBLISHED,
            defaults={
                "name": "B23 AI Semester 05 - Official V1",
                "valid_from": date(2026, 8, 31),
                "valid_to": date(2026, 12, 13),
            },
        )
        b23_ai_entries = [
            ("MONDAY", "08:15", "10:15", "CM3710", "1LH02A", "fernando_ksd", "AI-B23-Full", False, "LECTURE"),
            ("MONDAY", "10:30", "12:30", "IS3700", None, "perera_man", "AI-B23-Full", True, "LECTURE"),
            ("MONDAY", "13:15", "15:15", "CM3810", "3LH01A", "fernando_ksd", "AI-B23-Full", False, "LECTURE"),
            ("MONDAY", "15:30", "17:30", "CM3230", None, "silva_atp", "AI-B23-Full", True, "LECTURE"),
            ("TUESDAY", "15:30", "17:30", "CM3630", None, "karunananda_as", "AI-B23-Full", True, "LECTURE"),
            ("WEDNESDAY", "10:30", "12:30", "CM3430", "2LH01A", "thanuja_alarr", "AI-B23-Full", False, "LECTURE"),
            ("WEDNESDAY", "13:15", "15:15", "IN2321", "0LH01A", "ranawaka_radpm", "AI-B23-Full", False, "LECTURE"),
            ("THURSDAY", "08:15", "10:15", "CM3640", "0LH01A", "piyatilake_its", "AI-B23-Full", False, "LECTURE"),
            ("THURSDAY", "10:30", "11:30", None, "0LH01A", None, "AI-B23-Full", False, "LECTURE"),
            ("THURSDAY", "11:30", "12:30", None, "0LH01A", None, "AI-B23-Full", False, "LECTURE"),
            ("THURSDAY", "15:30", "17:30", "CM3610", None, "karunananda_as", "AI-B23-Full", True, "LECTURE"),
            ("FRIDAY", "10:30", "12:30", "CM3720", "1LH02A", "silva_atp", "AI-B23-Full", False, "LECTURE"),
            ("FRIDAY", "15:30", "17:30", "IN3101", "4LH02A", "premadasa_mgnn", "AI-B23-Full", False, "LAB"),
        ]
        self._populate_entries_if_empty(
            tenant, b23_ai_pub, b23_ai_entries, modules, lecturers, halls, groups
        )

        # 7C. Published Timetable for B23 ITM (from B23 - ITM Timetable.pdf)
        b23_itm_pub, _ = Timetable.objects.get_or_create(
            tenant=tenant,
            batch=batches["B23"],
            degree_program=degrees["ITM"],
            status=Timetable.Status.PUBLISHED,
            defaults={
                "name": "B23 ITM Semester 05 - Official V1",
                "valid_from": date(2026, 8, 31),
                "valid_to": date(2026, 12, 13),
            },
        )
        b23_itm_entries = [
            ("MONDAY", "08:15", "10:15", "IS3610", "4LH02A", "ganegoda_gu", "ITM-B23-Full", False, "LECTURE"),
            ("MONDAY", "10:30", "12:30", "IS3700", None, "perera_man", "ITM-B23-Full", True, "LECTURE"),
            ("MONDAY", "13:15", "15:15", "IS3120", "0LH02A", "sandanayake_tc", "ITM-B23-Full", False, "LECTURE"),
            ("MONDAY", "15:30", "17:30", "CM3211", None, "silva_atp", "ITM-B23-Full", True, "LECTURE"),
            ("TUESDAY", "08:15", "10:15", "IS3520", "1LH03A", "seneviratne_bld", "ITM-B23-Full", False, "LECTURE"),
            ("TUESDAY", "10:30", "12:30", "IS3011", "LAB1", "wijetunge_wasn", "ITM-IS3011-G1", False, "LAB"),
            ("TUESDAY", "10:30", "12:30", "IS3011", "LAB2", "wijetunge_wasn", "ITM-IS3011-G2", False, "LAB"),
            ("TUESDAY", "10:30", "12:30", "IS3011", "LAB3", "wijetunge_wasn", "ITM-IS3011-G3", False, "LAB"),
            ("TUESDAY", "13:15", "15:15", "IN3530", "1LH03A", "firdhous_mfm", "ITM-B23-Full", False, "LECTURE"),
            ("TUESDAY", "15:30", "17:30", "IN3320", "4LH02A", "sudantha_bh", "ITM-B23-Full", False, "LECTURE"),
            ("WEDNESDAY", "10:30", "12:30", "IS3510", "2LH02A", "ganegoda_gu", "ITM-B23-Full", False, "LECTURE"),
            ("WEDNESDAY", "13:15", "15:15", "IN3210", "1LH02A", "chandimali_mn", "ITM-B23-Full", False, "LECTURE"),
            ("WEDNESDAY", "15:30", "17:30", "CM3311", None, "karunananda_as", "ITM-B23-Full", True, "LECTURE"),
            ("THURSDAY", "10:30", "11:30", None, "0LH01A", None, "ITM-B23-Full", False, "LECTURE"),
            ("THURSDAY", "11:30", "12:30", None, "0LH01A", None, "ITM-B23-Full", False, "LECTURE"),
            ("THURSDAY", "13:15", "15:15", "IN3700", "4LH02A", "karunarathne_gti", "ITM-B23-Full", False, "LECTURE"),
            ("THURSDAY", "15:30", "17:30", "IS3920", "1LH03A", "seneviratne_bld", "ITM-B23-Full", False, "LECTURE"),
            ("FRIDAY", "08:15", "10:15", "IS3130", "1LH03A", "seneviratne_bld", "ITM-B23-Full", False, "LECTURE"),
            ("FRIDAY", "08:15", "10:15", "IS3020", "1LH02A", "wijetunge_wasn", "ITM-B23-Full", False, "LECTURE"),
            ("FRIDAY", "10:30", "12:30", "IN3311", "1LH03A", "premaratne_sc", "ITM-B23-Full", False, "LECTURE"),
            ("FRIDAY", "13:15", "15:15", "IS3200", "1LH03A", "upeksha_pgs", "ITM-B23-Full", False, "LECTURE"),
            ("FRIDAY", "15:30", "17:30", "IN3101", "4LH02A", "premadasa_mgnn", "ITM-B23-Full", False, "LAB"),
        ]
        self._populate_entries_if_empty(
            tenant, b23_itm_pub, b23_itm_entries, modules, lecturers, halls, groups
        )

        # 7D. Published Timetable for B24 IT (from B24 - IT time table.pdf)
        b24_it_pub, _ = Timetable.objects.get_or_create(
            tenant=tenant,
            batch=batches["B24"],
            degree_program=degrees["IT"],
            status=Timetable.Status.PUBLISHED,
            defaults={
                "name": "B24 IT Semester 03 - Official V1",
                "valid_from": date(2026, 6, 8),
                "valid_to": date(2026, 9, 20),
            },
        )
        b24_it_entries = [
            ("MONDAY", "08:15", "10:15", "IN2311", "0LH02A", "premaratne_sc", "IT-B24-Full", False, "LECTURE"),
            ("MONDAY", "10:30", "12:30", "IN2901", "4LH02A", "karunarathne_gti", "IT-B24-Full", False, "LAB"),
            ("TUESDAY", "08:15", "10:15", "IN2211", "4LH02A", "ahangama_s", "IT-B24-Full", False, "LECTURE"),
            ("TUESDAY", "10:30", "12:30", "CM2131", "0LH02A", "piyatilake_its", "IT-B24-Full", False, "LECTURE"),
            ("TUESDAY", "13:15", "15:15", "IN2201", "4LH02A", "amalraj_crj", "IT-B24-Full", False, "LECTURE"),
            ("WEDNESDAY", "08:15", "10:15", "DI1017", "1LH02A", "sandanayake_tc", "IT-B24-Full", False, "LECTURE"),
            ("WEDNESDAY", "10:30", "12:30", "DI1016", "1LH02A", "udalamaththa_s", "IT-B24-Full", False, "LECTURE"),
            ("WEDNESDAY", "13:15", "15:15", "CM2131", "4LH02A", "piyatilake_its", "IT-B24-Full", False, "TUTORIAL"),
            ("WEDNESDAY", "13:15", "15:15", "IN2321", None, "ranathunga_l", "IT-B24-Full", True, "LAB"),
            ("THURSDAY", "10:30", "11:30", None, "0LH01A", None, "IT-B24-Full", False, "LECTURE"),
            ("THURSDAY", "11:30", "12:30", None, "0LH01A", None, "IT-B24-Full", False, "LECTURE"),
            ("THURSDAY", "13:15", "15:15", "IN2101", "0LH02A", "thanthriwatta_tm", "IT-B24-Full", False, "LECTURE"),
            ("THURSDAY", "15:30", "17:30", "IN2201", None, "amalraj_crj", "IT-B24-Full", True, "LAB"),
            ("THURSDAY", "19:00", "21:00", "DI1015", None, "wijetunge_wasn", "IT-B24-Full", True, "LECTURE"),
            ("FRIDAY", "08:15", "10:15", "IN2321", "0LH02A", "ranathunga_l", "IT-B24-Full", False, "LECTURE"),
            ("FRIDAY", "10:30", "12:30", "IN2101", None, "thanthriwatta_tm", "IT-B24-Full", True, "LAB"),
            ("SATURDAY", "09:00", "11:00", "DI1015", None, "wijetunge_wasn", "IT-B24-Full", True, "LECTURE"),
        ]
        self._populate_entries_if_empty(
            tenant, b24_it_pub, b24_it_entries, modules, lecturers, halls, groups
        )

    def _populate_entries_if_empty(
        self, tenant, timetable, entry_rows, modules, lecturers, halls, groups
    ):
        if ScheduleEntry.objects.filter(timetable=timetable).exists():
            self.stdout.write(f"Timetable '{timetable.name}' already has entries, skipping")
            return

        for day, start, end, mod_code, hall_code, lec_user, grp_name, is_online, sess_type in entry_rows:
            module = modules[mod_code] if mod_code else None
            hall = halls[hall_code] if (hall_code and not is_online) else None
            lecturer = lecturers[lec_user] if lec_user else None

            event_name = None
            if module is None:
                event_name = "Guest Talk" if start == "10:30" else "Union Hour"

            entry = ScheduleEntry.objects.create(
                tenant=tenant,
                timetable=timetable,
                module=module,
                event_name=event_name,
                lecturer=lecturer,
                hall=hall,
                is_online=is_online,
                session_type=sess_type,
                day_of_week=day,
                start_time=start,
                end_time=end,
            )
            entry.student_groups.add(groups[grp_name])

        self.stdout.write(
            f"Timetable '{timetable.name}' (V{timetable.version}, {timetable.status}): {len(entry_rows)} entries seeded"
        )

    # ------------------------------------------------------------------
    # 8. Extra Test Users (HOD & Students)
    # ------------------------------------------------------------------
    def _seed_test_users(self, tenant):
        test_users = [
            ("hod_it", "hod.it@uom.lk", User.Role.HOD),
            ("hod_cm", "hod.cm@uom.lk", User.Role.HOD),
            ("student_b23_it", "b23.it.student@uom.lk", User.Role.STUDENT),
            ("student_b23_ai", "b23.ai.student@uom.lk", User.Role.STUDENT),
            ("student_b23_itm", "b23.itm.student@uom.lk", User.Role.STUDENT),
            ("student_b24_it", "b24.it.student@uom.lk", User.Role.STUDENT),
        ]
        created_count = 0
        for username, uom_email, role in test_users:
            user, created = User.objects.get_or_create(
                uom_email=uom_email,
                defaults={
                    "username": username,
                    "email": uom_email,
                    "tenant": tenant,
                    "role": role,
                    "is_uom_verified": True,
                },
            )
            if created:
                user.set_password("Lectra@2026")
                user.save()
                created_count += 1
        self.stdout.write(f"Test users ready (newly created: {created_count})")
