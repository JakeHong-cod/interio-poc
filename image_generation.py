import io
import urllib.parse
import pandas as pd
import requests
import streamlit as st
from PIL import Image

# ----------------------------------------------------
# 1. 페이지 기본 설정
# ----------------------------------------------------
st.set_page_config(page_title="스마트 인테리어 견적 진단기", layout="wide")

st.title("🏡 인테리어 견적 진단 & AI 비주얼라이저")
st.caption("공급 평형 선택 시 기본 공사비가 즉시 책정되며, 선택 옵션에 따라 최종 견적이 산출됩니다.")

# ----------------------------------------------------
# 2. 사이드바 - 단지 및 평형 선택 (평형별 기본 단가 정의)
# ----------------------------------------------------
st.sidebar.header("📍 1. 기본 정보 입력")

complex_name = st.sidebar.text_input("아파트 단지명", value="둔산 둥지아파트")

# 평형별 순수 기본 공사비 데이터 (평당 약 110~120만 원 수준의 올수리 기초 베이스)
# 옵션을 아무것도 추가하지 않아도 평형에 따라 기본 가격이 완전히 다르게 시작됩니다.
size_database = {
    "20평형 (전용 49㎡)": {"pyeong": 20, "base_price": 2300},
    "24평형 (전용 59㎡)": {"pyeong": 24, "base_price": 2800},
    "34평형 (전용 84㎡)": {"pyeong": 34, "base_price": 3950},
    "42평형 (전용 115㎡)": {"pyeong": 42, "base_price": 4900},
    "50평형 (전용 135㎡)": {"pyeong": 50, "base_price": 5850}
}

selected_size_label = st.sidebar.selectbox("공급 평형 선택", list(size_database.keys()), index=1)

current_pyeong = size_database[selected_size_label]["pyeong"]
default_base_cost = size_database[selected_size_label]["base_price"]  # 평형별 시작 기본가

# 옵션 자재량 계산을 위한 면적 계수 (24평 기준)
scale_factor = current_pyeong / 24.0

# ----------------------------------------------------
# 3. 사이드바 - 공정별 업그레이드 옵션 선택
# ----------------------------------------------------
st.sidebar.header("🛠 2. 공정별 업그레이드 옵션")

material_tier = st.sidebar.radio("자재 등급", ["실속형 (가성비 중심)", "표준형 (가장 선호)", "고급형 (프리미엄 자재)"], index=1)

# 24평 기준 옵션 추가금 데이터 (기본 사양 대비 추가/변경 비용, 단위: 만 원)
floor_dict = {
    "강마루 기본 마감 (기본 포함)": 0,
    "원목마루 프리미엄 마감 (업그레이드)": 260,
    "600각 포세린 타일 마감 (업그레이드)": 330
}
wall_dict = {
    "친환경 실크 도배 (기본 포함)": 0,
    "벤자민무어 도장 마감": 230,
    "벽면 히든도어 & 친환경 도장 마감": 470
}
kitchen_dict = {
    "기존 일자/ㄱ자 구조 유지 (기본 포함)": 0,
    "대면형 아일랜드 구조 변경": 330,
    "세라믹 상판 & 프리미엄 빌트인 가구": 680
}
bath_dict = {
    "기본 타일 덧방 시공 (기본 포함)": 0,
    "전체 철거 및 조적 세면대 (2개소)": 330,
    "호텔식 대형 졸리컷 타일 & 매립수전": 600
}

floor_option = st.sidebar.selectbox("바닥 마감재 변경", list(floor_dict.keys()), index=0)
wall_option = st.sidebar.selectbox("벽체 / 아트월 변경", list(wall_dict.keys()), index=0)
kitchen_option = st.sidebar.selectbox("주방 레이아웃 변경", list(kitchen_dict.keys()), index=0)
bath_option = st.sidebar.selectbox("욕실 공사 범위 변경", list(bath_dict.keys()), index=0)

# ----------------------------------------------------
# 4. 견적 연산 로직 (평형 기본가 + 평형 연동 옵션 추가금)
# ----------------------------------------------------
# 옵션 추가금에 평형 면적 가중치 반영
opt_floor_cost = int(floor_dict[floor_option] * scale_factor)
opt_wall_cost = int(wall_dict[wall_option] * scale_factor)
opt_kitchen_cost = int(kitchen_dict[kitchen_option] * (1.0 + (scale_factor - 1.0) * 0.7))
opt_bath_cost = int(bath_dict[bath_option] * (1.0 + (scale_factor - 1.0) * 0.5))

options_sum = opt_floor_cost + opt_wall_cost + opt_kitchen_cost + opt_bath_cost

# 자재 등급별 계수
tier_multipliers = {
    "실속형 (가성비 중심)": 0.92,
    "표준형 (가장 선호)": 1.0,
    "고급형 (프리미엄 자재)": 1.18
}
tier_mult = tier_multipliers[material_tier]

# 최종 금액 산출: (평형별 기본가 + 옵션 추가금) * 등급 계수
final_calculated_cost = int((default_base_cost + options_sum) * tier_mult)

total_cost_min = int(final_calculated_cost * 0.96)
total_cost_max = int(final_calculated_cost * 1.06)

# ----------------------------------------------------
# 5. 견적 화면 출력 UI
# ----------------------------------------------------
col1, col2 = st.columns([1.2, 1])

with col1:
    st.subheader(f"📋 {complex_name} ({selected_size_label}) 상세 견적표")
    
    table_data = [
        {"공정 구분": "평형 기본 인테리어 베이스", "내역 및 사양": f"{current_pyeong}평형 기본 올수리 (철거/전기/창호/기본설비 일체)", "예상 금액(만 원)": f"{default_base_cost:,}"},
        {"공정 구분": "바닥 옵션", "내역 및 사양": f"{floor_option} ({current_pyeong}평 적용)", "예상 금액(만 원)": f"+{opt_floor_cost:,}" if opt_floor_cost > 0 else "기본 포함"},
        {"공정 구분": "벽체 옵션", "내역 및 사양": f"{wall_option} ({current_pyeong}평 적용)", "예상 금액(만 원)": f"+{opt_wall_cost:,}" if opt_wall_cost > 0 else "기본 포함"},
        {"공정 구분": "주방 구조 옵션", "내역 및 사양": kitchen_option, "예상 금액(만 원)": f"+{opt_kitchen_cost:,}" if opt_kitchen_cost > 0 else "기본 포함"},
        {"공정 구분": "욕실 구조 옵션", "내역 및 사양": bath_option, "예상 금액(만 원)": f"+{opt_bath_cost:,}" if opt_bath_cost > 0 else "기본 포함"}
    ]
    
    df = pd.DataFrame(table_data)
    st.table(df)

with col2:
    st.subheader("💰 예상 총 공사비 범위")
    st.metric(
        label=f"{complex_name} ({selected_size_label})",
        value=f"{total_cost_min:,}만 ~ {total_cost_max:,}만 원"
    )
    st.success(f"🏠 **{current_pyeong}평형 기본 착수 시작가**: **{default_base_cost:,}만 원**")
    st.info(f"💡 자재 등급: **{material_tier}** | 추가 옵션 총액: **+{options_sum:,}만 원**")
    st.button("📄 시공사 상담용 브리프(PDF) 출력하기")

# ----------------------------------------------------
# 6. 초고화질 AI 렌더링 모듈
# ----------------------------------------------------
st.divider()
st.subheader("📸 AI 초고화질 리모델링 디자인 렌더링")

uploaded_file = st.file_uploader(
    "현장 방 사진 업로드 (선택사항)", type=["jpg", "jpeg", "png", "webp"]
)

structural_note = st.text_area(
    "추가 디자인 요청 사항 / 레이아웃 메모",
    placeholder='예: "따뜻한 베이지 우드 톤, 실링팬 설치, 주방 간접조명 강조"',
)

if uploaded_file:
    input_image = Image.open(uploaded_file)
    st.image(input_image, caption="업로드된 현재 현장 사진", width=320)

if st.button("🎨 AI 초고화질 시안 생성하기", type="primary"):
    features_en = [f"{current_pyeong} pyeong open layout Korean apartment interior space"]
    for item in [floor_option, wall_option, kitchen_option]:
        if "원목" in item:
            features_en.append("premium natural oak herringbone wood flooring")
        elif "포세린" in item:
            features_en.append("large 600x600 matte beige porcelain floor tiles")
        elif "도장" in item or "히든" in item:
            features_en.append("flawless seamless painted walls with trimless hidden doors")
        elif "아일랜드" in item:
            features_en.append("modern open kitchen with minimalist waterfall center island")
        elif "세라믹" in item:
            features_en.append("premium ceramic stone countertop with custom built-in cabinetry")

    features_str = ", ".join(features_en)
    clean_tier = material_tier.split(" ")[0]

    prompt = (
        f"Award winning luxury Korean apartment interior design, {clean_tier} grade, "
        f"{features_str}, photorealistic interior architectural photography, "
        f"Architectural Digest feature, soft warm ambient lighting, natural morning sunlight through sheer curtains, "
        f"clean lines, ultra realistic high textures, 8k resolution, Unreal Engine 5 render style, hyper-detailed"
    )

    if structural_note:
        prompt += f", design requirements: {structural_note}"

    encoded_prompt = urllib.parse.quote(prompt)

    with st.spinner("AI가 선택하신 평형과 자재를 분석하여 초고화질 렌더링 시안을 생성 중입니다..."):
        try:
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&model=flux&nologo=true&seed=42"
            response = requests.get(image_url, timeout=40)
            if response.status_code == 200:
                result_image = Image.open(io.BytesIO(response.content))
                st.image(result_image, caption=f"AI 리모델링 추천 렌더링 시안 ({selected_size_label} / {clean_tier})")

                buf = io.BytesIO()
                result_image.save(buf, format="PNG")
                st.download_button(
                    "📥 고화질 시안 다운로드 (PNG)",
                    data=buf.getvalue(),
                    file_name="interior_design_render.png",
                    mime="image/png"
                )

                st.warning(
                    "⚠ 본 시안은 시각적 디자인 컨셉트 참고용입니다. 실제 철거 가능 여부 및 상세 치수는 현장 실측을 통해 확정됩니다."
                )
            else:
                st.error("이미지 서버와의 통신에 실패했습니다. 잠시 후 다시 시도해 주세요.")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")