import os

from dotenv import load_dotenv
from flask import Blueprint, render_template
from supabase import create_client

load_dotenv()

# 메인 블루프린트 생성
main_bp = Blueprint("main", __name__)


def _format_price(price_value) -> str:
    """숫자 가격을 천 단위 구분 쉼표와 '원'을 붙여 형식화합니다."""
    try:
        return f"{int(price_value):,}원"
    except (TypeError, ValueError):
        return "0원"


@main_bp.route("/")
def index():
    """메인 인덱스 페이지: Supabase에서 추천 상품 4개를 불러옵니다.
    로드가 실패하거나 데이터가 없으면 빈 리스트로 대체됩니다."""
    products = []

    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_anon_key:
            raise ValueError("SUPABASE_URL or SUPABASE_ANON_KEY is missing")

        client = create_client(supabase_url, supabase_anon_key)
        response = (
            client.table("products")
            .select("name, price, thumbnail_url")
            .eq("is_active", True)
            .eq("is_featured", True)
            .limit(4)
            .execute()
        )

        raw_products = response.data or []
        for item in raw_products:
            products.append(
                {
                    "name": item.get("name") or "상품명 없음",
                    "price": _format_price(item.get("price")),
                    "thumbnail_url": item.get("thumbnail_url")
                    or "https://picsum.photos/seed/fashion-fallback/500/600",
                }
            )
    except Exception as exc:
        print(f"[SupabaseError] Failed to load featured products: {exc}")
        products = []  # 에러 발생 시 빈 리스트로 대체

    return render_template("index.html", products=products)
