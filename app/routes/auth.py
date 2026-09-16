import os
from functools import wraps

from dotenv import load_dotenv
from flask import Blueprint, redirect, render_template, request, session, url_for
from supabase import create_client

load_dotenv()

# 회원가입 및 로그인 처리를 위한 인증 블루프린트 생성
auth_bp = Blueprint("auth", __name__)
_supabase_client = None


def _build_supabase_client():
	"""Supabase 클라이언트를 초기화하여 반환합니다. (싱글톤 패턴과 유사하게 전역 변수에 저장)"""
	global _supabase_client
	if _supabase_client is not None:
		return _supabase_client

	supabase_url = os.getenv("SUPABASE_URL")
	supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
	if not supabase_url or not supabase_anon_key:
		raise ValueError("SUPABASE_URL or SUPABASE_ANON_KEY is missing")

	_supabase_client = create_client(supabase_url, supabase_anon_key)
	return _supabase_client


def login_required(view_func):
	"""로그인이 필요한 페이지에 적용되는 데코레이터입니다.
	세션에 'user_id'가 없으면 로그인 페이지로 리다이렉트합니다."""
	@wraps(view_func)
	def wrapped(*args, **kwargs):
		if not session.get("user_id"):
			return redirect(url_for("auth.login"))
		return view_func(*args, **kwargs)

	return wrapped


@auth_bp.get("/login") # 기존 '/auth/login'에서 blueprint prefix가 '/auth'이므로 '/login'으로 처리
def login():
	"""로그인 페이지 렌더링. 이미 로그인된 사용자는 메인(인덱스)으로 이동합니다."""
	if session.get("user_id"):
		return redirect(url_for("main.index"))

	error = request.args.get("error")
	error_description = request.args.get("error_description")
	return render_template(
		"auth/login.html",
		error=error,
		error_description=error_description,
	)


@auth_bp.get("/microsoft") # blueprint prefix '/auth'가 지정되므로 '/microsoft'로 처리
def microsoft_login():
	"""Microsoft OAuth 로그인을 시작합니다. Supabase OAuth URL로 리다이렉트합니다."""
	try:
		client = _build_supabase_client()
		site_url = os.getenv("SITE_URL", "http://localhost:5000").rstrip("/")
		redirect_to = f"{site_url}/auth/callback"

		try:
			oauth_response = client.auth.sign_in_with_oauth(
				provider="azure",
				options={"redirect_to": redirect_to},
			)
		except TypeError:
			oauth_response = client.auth.sign_in_with_oauth(
				{
					"provider": "azure",
					"options": {"redirect_to": redirect_to},
				}
			)

		oauth_url = None
		if hasattr(oauth_response, "url"):
			oauth_url = oauth_response.url
		elif hasattr(oauth_response, "data") and oauth_response.data:
			oauth_url = oauth_response.data.get("url")

		if not oauth_url:
			raise ValueError("OAuth redirect URL was not returned")

		return redirect(oauth_url)
	except Exception as exc:
		print(f"[AuthError] Microsoft OAuth start failed: {exc}")
		return redirect(url_for("auth.login", error="microsoft_failed"))


@auth_bp.get("/callback") # blueprint prefix '/auth'가 지정되므로 '/callback'으로 처리
def auth_callback():
	"""Supabase OAuth 인증 콜백을 처리합니다. authorization code를 세션으로 교환합니다."""
	error = request.args.get("error")
	error_description = request.args.get("error_description")
	if error:
		print(f"[AuthError] OAuth provider callback error: {error} - {error_description}")
		return redirect(
			url_for(
				"auth.login",
				error="callback_failed",
				error_description=error_description or error,
			)
		)

	code = request.args.get("code")
	if not code:
		return redirect(url_for("auth.login", error="callback_failed"))

	try:
		client = _build_supabase_client()
		auth_response = client.auth.exchange_code_for_session({"auth_code": code})

		user = getattr(auth_response, "user", None)
		if user is None:
			user = getattr(getattr(auth_response, "session", None), "user", None)

		user_id = getattr(user, "id", None)
		email = getattr(user, "email", None)

		if not user_id:
			raise ValueError("User session was not created")

		session["user_id"] = user_id
		session["email"] = email
		return redirect(url_for("auth.mypage"))  # mypage 라우트로 안전하게 이동
	except Exception as exc:
		print(f"[AuthError] OAuth callback failed: {exc}")
		return redirect(url_for("auth.login", error="callback_failed"))


@auth_bp.get("/logout") # prefix '/auth'가 붙어 '/auth/logout'으로 동작
def logout():
	"""로그아웃을 처리합니다. Supabase 세션을 종료하고 Flask 세션을 비웁니다."""
	try:
		client = _build_supabase_client()
		client.auth.sign_out()
	except Exception as exc:
		print(f"[AuthError] Supabase sign-out failed: {exc}")

	session.pop("user_id", None)
	session.pop("email", None)
	return redirect(url_for("main.index"))


@auth_bp.get("/mypage") # prefix '/auth'가 붙으므로 '/auth/mypage'가 됨 (또는 App 전체에서 /mypage로 하려면 blueprint 외부거나 app_errorhandler 등 고려 또는 template url_for 수정 필요)
@login_required
def mypage():
	"""마이페이지 렌더링. 세션 이메일 정보를 함께 템플릿에 보냅니다."""
	return render_template("auth/mypage.html", email=session.get("email"))
