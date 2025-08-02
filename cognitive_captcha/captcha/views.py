from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
from django.shortcuts import render, redirect
from .models import CaptchaAttempt, CaptchaChallenge
import json
import random

def get_identifier(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

def captcha_page(request):
    return render(request, 'captcha_page.html')

def protected_page(request):
    if not request.session.get("captcha_passed", False):
        return redirect('/')
    return render(request, 'protected_page.html')

@csrf_protect
@require_http_methods(["GET"])
def get_captcha(request):
    identifier = get_identifier(request)
    attempt, _ = CaptchaAttempt.get_or_create_for_identifier(identifier)
    
    if attempt.is_blocked and attempt.blocked_until > timezone.now():
        return JsonResponse({'status': 'blocked'}, status=403)
    
    difficulty = determine_difficulty(attempt.attempts)
    challenge = generate_challenge(difficulty)
    
    captcha = CaptchaChallenge.objects.create(
        identifier=identifier,
        expires_at=timezone.now() + timezone.timedelta(minutes=5),
        **challenge
    )
    
    return JsonResponse({
        'id': captcha.id,
        'difficulty': difficulty,
        'time_limit': 60 if difficulty >= 2 else None,
        **challenge
    })

def determine_difficulty(attempts):
    if attempts >= 6: return 3
    if attempts >= 3: return 2
    return 1

def generate_challenge(difficulty):
    params = {
        1: {'actors': 3, 'speed': 1.0},
        2: {'actors': 4, 'speed': 1.2},
        3: {'actors': 5, 'speed': 1.5},
    }[difficulty]
    
    scene = random.choice(['room', 'park', 'street', 'cafe'])
    colors = ['red', 'green', 'blue', 'yellow']
    actors = [
        {
            'color': random.choice(colors),
            'delay': i * 0.5,
            'speed': random.uniform(0.8, 1.2) * params['speed'],
            'object': f"item_{random.choice(colors)}" if i == 0 else None
        } 
        for i in range(params['actors'])
    ]
    
    question = "What color was the item?" if random.random() > 0.5 else "Which color moved first?"
    correct = next(a['object'].split('_')[1] if a['object'] else a['color'] for a in actors if a['object'] or question.endswith('first?'))
    
    return {
        'scene': scene,
        'question': question,
        'options': random.sample(colors, 3) + [correct],
        'correct_answer': correct,
        'animation_data': {'actors': actors},
    }

@csrf_protect
@require_http_methods(["POST"])
def submit_captcha_answer(request):
    try:
        data = json.loads(request.body)
        identifier = get_identifier(request)
        attempt, _ = CaptchaAttempt.get_or_create_for_identifier(identifier)
        
        if attempt.is_blocked:
            return JsonResponse({'status': 'blocked'}, status=403)
        
        try:
            challenge = CaptchaChallenge.objects.get(
                id=data['id'],
                identifier=identifier,
                expires_at__gt=timezone.now(),
                used=False
            )
        except CaptchaChallenge.DoesNotExist:
            return JsonResponse({'status': 'invalid'}, status=400)
        
        is_correct = str(challenge.correct_answer).lower() == str(data['answer']).lower()
        
        if is_correct:
            attempt.attempts = 0
            request.session['captcha_passed'] = True
            status = 'passed'
        else:
            attempt.attempts += 1
            if attempt.attempts >= 10:
                attempt.is_blocked = True
                attempt.blocked_until = timezone.now() + timezone.timedelta(hours=1)
            status = 'failed'
        
        attempt.save()
        challenge.used = True
        challenge.save()
        
        return JsonResponse({
            'status': status,
            'attempts': attempt.attempts,
            'difficulty': determine_difficulty(attempt.attempts)
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)