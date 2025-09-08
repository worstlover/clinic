# patient_monitoring/views.py

from django.shortcuts import render, get_object_or_404
from core.models import Patient
from visits.models import Visit
from lab_results.models import PeriodicExamination, ClinicalMeasurement, LabParameterResult, TestType
from collections import defaultdict
import jdatetime

CHART_CONFIG = {
    'lipid_profile': {
        'title': 'نمودار چربی خون (mg/dL)',
        'yAxisTitle': 'مقدار (mg/dL)',
        'tests': {
            'Cholesterol': {'label': 'کلسترول', 'borderColor': 'rgb(153, 102, 255)'},
            'Triglycerides': {'label': 'تری گلیسیرید', 'borderColor': 'rgb(255, 159, 64)'},
            'LDL': {'label': 'LDL', 'borderColor': 'rgb(255, 99, 132)'},
            'HDL': {'label': 'HDL', 'borderColor': 'rgb(75, 192, 192)'},
        }
    },
    'thyroid_panel': {
        'title': 'نمودار تیروئید',
        'yAxisTitle': 'مقدار',
        'tests': {
            'T3': {'label': 'T3', 'borderColor': 'rgb(54, 162, 235)'},
            'T4': {'label': 'T4', 'borderColor': 'rgb(255, 205, 86)'},
            'TSH': {'label': 'TSH', 'borderColor': 'rgb(201, 203, 207)'},
        }
    },
    'cbc_panel': {
        'title': 'نمودار شمارش سلول‌های خونی',
        'yAxisTitle': 'مقدار',
        'tests': {
            'Hemoglobin': {'label': 'هموگلوبین (g/dL)', 'borderColor': 'rgb(255, 99, 132)'},
            'Hematocrit': {'label': 'هماتوکریت (%)', 'borderColor': 'rgb(10, 50, 200)'},
            'Platelet': {'label': 'پلاکت (K/uL)', 'borderColor': 'rgb(150, 20, 10)'},
        }
    }
}


def patient_report_view(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)

    height_cm = patient.height_cm
    if not height_cm or height_cm <= 0:
        latest_visit_with_height = Visit.objects.filter(
            patient=patient, height_cm__isnull=False, height_cm__gt=0
        ).order_by('-visit_date').first()
        if latest_visit_with_height:
            height_cm = latest_visit_with_height.height_cm
    height_m = float(height_cm) / 100 if height_cm else None

    visits = list(Visit.objects.filter(patient=patient).order_by('visit_date'))
    periodic_exams = list(PeriodicExamination.objects.filter(patient=patient).order_by('exam_date'))

    all_records = sorted(
        visits + periodic_exams,
        key=lambda x: x.visit_date.date() if hasattr(x, 'visit_date') else x.exam_date
    )

    all_test_names = []
    for chart_id, config in CHART_CONFIG.items():
        all_test_names.extend(config['tests'].keys())
    all_test_names.append('FBS')

    test_types_qs = TestType.objects.filter(name__in=all_test_names)
    test_type_map = {tt.name: tt for tt in test_types_qs}

    lab_results_params = LabParameterResult.objects.filter(
        periodic_exam__patient=patient
    ).select_related('periodic_exam', 'test_type').order_by('periodic_exam__exam_date')
    
    lab_data_by_exam = defaultdict(dict)
    for result in lab_results_params:
        lab_data_by_exam[result.periodic_exam.id][result.test_type.name] = result.result_value

    unified_data = []
    chart_dates = []
    
    chart_weights = []
    chart_bmis = []
    chart_systolic_bp = []
    chart_diastolic_bp = []
    chart_blood_sugars = []
    
    lab_chart_data = defaultdict(lambda: defaultdict(list))
    fbs_type_name = 'FBS'

    for item in all_records:
        date = item.visit_date if hasattr(item, 'visit_date') else item.exam_date
        
        # تبدیل تاریخ میلادی به شمسی برای نمایش در نمودار
        jdate = jdatetime.date.fromgregorian(date=date)
        date_str = str(jdate)
        chart_dates.append(date_str)
        
        data_point = {'date': jdate}
        weight = None
        systolic_bp = None
        diastolic_bp = None
        blood_sugar = None
        visit_height = None
        reason_for_visit = None
        treatment_result = None

        if isinstance(item, Visit):
            data_point['type'] = 'ویزیت'
            reason_for_visit = item.reason_for_visit.name if item.reason_for_visit else "نامشخص"
            treatment_result = item.treatment_result.name if item.treatment_result else "نامشخص"
            weight = item.weight_kg
            visit_height = item.height_cm
            if item.blood_pressure and '/' in item.blood_pressure:
                try:
                    systolic_bp, diastolic_bp = map(int, item.blood_pressure.split('/'))
                except ValueError: pass
            blood_sugar = float(item.blood_sugar) if item.blood_sugar else None
        
        elif isinstance(item, PeriodicExamination):
            data_point['type'] = 'معاینه دوره‌ای'
            reason_for_visit = item.overall_notes
            treatment_result = "نتیجه درمان در مدل معاینه دوره‌ای موجود نیست."
            try:
                measurements = ClinicalMeasurement.objects.get(periodic_exam=item)
                weight = measurements.weight
                systolic_bp = measurements.systolic_bp
                diastolic_bp = measurements.diastolic_bp
            except ClinicalMeasurement.DoesNotExist: pass
            
            if item.id in lab_data_by_exam:
                exam_results = lab_data_by_exam[item.id]
                if fbs_type_name in exam_results:
                    try: blood_sugar = float(exam_results[fbs_type_name])
                    except (ValueError, TypeError): pass

        chart_weights.append(float(weight) if weight is not None else None)
        chart_systolic_bp.append(systolic_bp)
        chart_diastolic_bp.append(diastolic_bp)
        chart_blood_sugars.append(blood_sugar)
        
        if height_m and weight is not None:
            bmi = float(weight) / (height_m ** 2)
            chart_bmis.append(round(bmi, 2))
        else:
            chart_bmis.append(None)
        
        exam_results = lab_data_by_exam.get(item.id, {}) if isinstance(item, PeriodicExamination) else {}
        for chart_id, config in CHART_CONFIG.items():
            for test_name in config['tests']:
                value = exam_results.get(test_name)
                try: lab_chart_data[chart_id][test_name].append(float(value) if value is not None else None)
                except (ValueError, TypeError): lab_chart_data[chart_id][test_name].append(None)

        data_point.update({
            'weight': weight,
            'height': visit_height,
            'blood_sugar': blood_sugar,
            'blood_pressure': f"{systolic_bp}/{diastolic_bp}" if systolic_bp and diastolic_bp else None,
            'lab_results': exam_results,
            'reason_for_visit': reason_for_visit,
            'treatment_result': treatment_result,
        })
        unified_data.append(data_point)
    
    chart_data = {
        'dates': chart_dates,
        'base_charts': {
            'weights': chart_weights,
            'bmis': chart_bmis,
            'systolic_bp': chart_systolic_bp,
            'diastolic_bp': chart_diastolic_bp,
            'blood_sugars': chart_blood_sugars,
        },
        'lab_charts_config': CHART_CONFIG,
        'lab_charts_data': lab_chart_data
    }

    context = {
        'patient': patient,
        'all_data': unified_data,
        'chart_data': chart_data,
        'height_cm': height_cm,
    }

    return render(request, 'patient_monitoring/patient_report.html', context)