from django.shortcuts import render

def index(request):
    return render(request, 'app_course_intro/index.html')

def api_introduction(request):
    return render(request, 'app_course_intro/api_introduction.html')

def course_introduction(request):
    return render(request, 'app_course_intro/course_introduction.html')
