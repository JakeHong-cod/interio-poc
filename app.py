import io
import pandas as pd
import streamlit as st
from PIL import Image
from google import genai
from google.genai.types import GenerateContentConfig, Modality

# ----------------------------------------------------
# 1. 모바일 및 다크모드 대응 전역 설정
# ----------------------------------------------------
st.set_page_config(
    page_title="스마트 인테리어 견적 & AI 비주얼라이저",
    page_icon="🏡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .stButton>button {
        width: 100%;
        height: 3.2rem;
        font-size: 1.05rem;
        font-weight: bold;
        border-radius: 8px;
    }
    .price-card {
        background-color: #f1f5f9 !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        text-align: center;
    }
    .price-card-title {
        color: #475569 !important;
        font-size: 0.95rem;
        font-weight: 600;
        margin-bottom: 0.4rem;
    }
    .price-card-value {
        color: #0f172a !important;
        font-size: 1.8rem;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
</style>
""", unsafe_allow_html=True)

MAX_FREE_CREDITS = 3

if "generation_count" not in st.session_state:
    st.session_state.generation_count = 0

if "rendered_image" not in st.session_state:
    st.session_state.rendered_image = None

st.title("🏡 인테리어 견적 진단 & AI 비주얼라이저")
st.caption("공급 평형과 옵션에 따른 견적 산출과 Gemini AI 디렉터 기반 3D 리모델링 시안을 제공합니다.")

# ----------------------------------------------------
# 2. 메인 화면 1단계: 기본 정보 선택
# ----------------------------------------------------
st.markdown("### 📍 1. 기본 정보 선택")

complex_name = st.text_input("아파트 단지명", value="둔산 둥지아파트")

size_database = {
    "20평형 (전용 49㎡)": {"pyeong": 20, "base_price": 2300},
    "24평형 (전용 59㎡)": {"pyeong": 24, "base_price": 2800},
    "34평형 (전용 84㎡)": {"pyeong": 34, "base_price": 3950},
    "42평형 (전용 115㎡)": {"pyeong": 42, "base_price": 4900},
    "50평형 (전용 135㎡)": {"pyeong": 50, "base_price": 5850}
}

selected_size_label = st.selectbox("공급 평형 선택", list(size_database.keys()), index=1)

current_pyeong = size_database[selected_size_label]["pyeong"]
raw_base_cost = size_database[selected_size_label]["base_price"]
scale_factor = current_pyeong / 24.0

# ----------------------------------------------------
# 3. 메인 화면 2단계: 공정별 옵션 선택
# ----------------------------------------------------
st.markdown("### 🛠 2. 공정별 업그레이드 옵션")

material_tier = st.radio("자재 등급 선택", ["실속형 (가성비 중심)", "표준형 (가장 선호)", "고급형 (프리미엄 자재)"], index=1)

tier_multipliers = {
    "실속형 (가성비 중심)": 0.90,
    "표준형 (가장 선호)": 1.0,
    "고급형 (프리미엄 자재)": 1.20
}
tier_mult = tier_multipliers[material_tier]

floor_dict = {
    "강마루 기본 마감 (기본 포함)": 0,
    "원목마루 프리미엄 마감 (업그레이드)": 260,
    "600각 포세린 타일 마감 (업그레이드)": 330
}
wall_dict = {
    "친환경 실크 도배 (기본 포함)": 0,
    "벤자민무어 친환경 도장 마감": 230,
    "벽면 히든도어 & 도장 마감": 470
}
kitchen_dict = {
    "기존 레이아웃 유지 (기본 포함)": 0,
    "대면형 아일랜드 구조 변경": 330,
    "세라믹 상판 & 프리미엄 빌트인 가구": 680
}
bath_dict = {
    "기본 덧방 시공 (기본 포함)": 0,
    "전체 철거 및 조적 세면대 (2개소)": 330,
    "호텔식 대형 졸리컷 타일 & 매립수전": 600
}

floor_option = st.selectbox("바닥 마감재", list(floor_dict.keys()), index=0)
wall_option = st.selectbox("벽체 / 아트월", list(wall_dict.keys()), index=0)
kitchen_option = st.selectbox("주방 레이아웃", list(kitchen_dict.keys()), index=0)
bath_option = st.selectbox("욕실 공사 범위", list(bath_dict.keys()), index=0)

# ----------------------------------------------------
# 4. 실시간 견적 산출 로직
# ----------------------------------------------------
default_base_cost = int(raw_base_cost * tier_mult)

opt_floor_cost = int(floor_dict[floor_option] * scale_factor * tier_mult)
opt_wall_cost = int(wall_dict[wall_option] * scale_factor * tier_mult)
opt_kitchen_cost = int(kitchen_dict[kitchen_option] * (1.0 + (scale_factor - 1.0) * 0.7) * tier_mult)
opt_bath_cost = int(bath_dict[bath_option] * (1.0 + (scale_factor - 1.0) * 0.5) * tier_mult)

options_sum = opt_floor_cost + opt_wall_cost + opt_kitchen_cost + opt_bath_cost

final_calculated_cost = default_base_cost + options_sum
total_cost_min = int(final_calculated_cost * 0.98)
total_cost_max = int(final_calculated_cost * 1.05)

# ----------------------------------------------------
# 5. 견적 결과 카드 및 상세표
# ----------------------------------------------------
st.divider()
st.markdown("### 💰 실시간 예상 공사비")

st.markdown(f"""
<div class="price-card">
    <div class="price-card-title">{complex_name} ({selected_size_label}) 예상 총 견적</div>
    <div class="price-card-value">{total_cost_min:,}만 ~ {total_cost_max:,}만 원</div>
</div>
""", unsafe_allow_html=True)

st.success(f"🏠 **{current_pyeong}평형 {material_tier.split(' ')[0]} 기본 시작가**: **{default_base_cost:,}만 원** (옵션 추가: +{options_sum:,}만 원)")

with st.expander("📋 공정별 세부 견적 내역서 보기 (터치하여 펼치기)"):
    table_data = [
        {"공정 구분": f"기본 베이스 ({material_tier.split(' ')[0]})", "내역": f"{current_pyeong}평형 기본 철거/전기/가설 일체", "금액(만 원)": f"{default_base_cost:,}"},
        {"공정 구분": "바닥 옵션", "내역": f"{floor_option}", "금액(만 원)": f"+{opt_floor_cost:,}" if opt_floor_cost > 0 else "기본 포함"},
        {"공정 구분": "벽체 옵션", "내역": f"{wall_option}", "금액(만 원)": f"+{opt_wall_cost:,}" if opt_wall_cost > 0 else "기본 포함"},
        {"공정 구분": "주방 옵션", "내역": f"{kitchen_option}", "금액(만 원)": f"+{opt_kitchen_cost:,}" if opt_kitchen_cost > 0 else "기본 포함"},
        {"공정 구분": "욕실 옵션", "내역": f"{bath_option}", "금액(만 원)": f"+{opt_bath_cost:,}" if opt_bath_cost > 0 else "기본 포함"}
    ]
    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

# ----------------------------------------------------
# 6. LLM 디렉팅 기반 2단계 AI 렌더링 파이프라인
# ----------------------------------------------------
st.divider()
st.markdown("### 📸 AI 리모델링 디자인 시안")

remaining_credits = MAX_FREE_CREDITS - st.session_state.generation_count

if remaining_credits > 0:
    st.markdown(f"🎟 **무료 생성 가능 횟수**: `{remaining_credits} / {MAX_FREE_CREDITS}회`")
else:
    st.error("🎟 무료 생성 횟수가 모두 소진되었습니다. (0/3회)")

api_key = None
try:
    api_key = st.secrets.get("GEMINI_API_KEY", None)
except Exception:
    pass

if not api_key:
    api_key = st.text_input(
        "Gemini API 키 입력 (secrets 미설정 시)",
        type="password"
    )

uploaded_file = st.file_uploader(
    "현장 방 사진 업로드 (스마트폰 앨범 또는 촬영)", type=["jpg", "jpeg", "png", "webp"]
)

structural_note = st.text_area(
    "추가 디자인 요청 사항 (자유롭게 입력)",
    placeholder='예: "우드톤이지만 너무 올드하지 않고 인스타 카페 같은 화사한 분위기, 주방 아일랜드와 천장 간접조명 강조"',
)

input_image = None
if uploaded_file:
    input_image = Image.open(uploaded_file)
    st.image(input_image, caption="업로드된 원본 현장 사진", use_container_width=True)

if remaining_credits > 0:
    if st.button("🎨 AI 3D 디자인 시안 생성하기", type="primary"):
        if not api_key:
            st.error("Gemini API 키를 입력하거나 secrets.toml에 등록해 주세요.")
        elif not uploaded_file:
            st.error("변환할 방 사진을 스마트폰에서 먼저 업로드해 주세요.")
        else:
            st.session_state.generation_count += 1
            client = genai.Client(api_key=api_key)

            # [1단계] Gemini Flash LLM 디렉터: 사용자 자연어 및 옵션을 초정밀 영문 프롬프트로 변환
            with st.spinner("AI 수석 디자이너가 고객님의 요청사항을 정밀 분석 중입니다..."):
                try:
                    clean_tier = material_tier.split(" ")[0]
                    prompt_director_query = f"""
You are a world-class architectural interior director.
Transform the following remodeling specifications and user requests into an ultra-detailed, photorealistic 3D interior rendering prompt in English.

[Project Info]
- Space: {current_pyeong} pyeong modern Korean apartment
- Material Grade: {clean_tier}
- Selected Finishes: Flooring ({floor_option}), Walls ({wall_option}), Kitchen ({kitchen_option}), Bathroom ({bath_option})
- User Custom Needs (Korean): "{structural_note if structural_note else 'Clean, cozy, modern minimalism'}"

[Prompt Crafting Rules]
1. MUST strictly instruct to preserve the exact camera perspective, depth, window placement, and wall/ceiling structure of the input image.
2. Translate abstract user requests (e.g., 'cafe mood', 'cozy wood tone', 'hotel vibe') into specific lighting temperatures (3000K warm cove light), material textures, and architectural details.
3. Output ONLY the refined English prompt paragraph without any markdown, bullet points, or conversational text.
"""
                    llm_res = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt_director_query
                    )
                    enhanced_prompt = llm_res.text.strip()

                except Exception as e:
                    enhanced_prompt = (
                        f"Photorealistic 3D interior photography of a {current_pyeong} pyeong modern Korean apartment, "
                        f"strictly preserving original room layout and camera angle, high end finishes: {floor_option}, {wall_option}, {kitchen_option}, "
                        f"soft natural daylight, Architectural Digest magazine quality, 8k resolution"
                    )

            # [2단계] Imagen 3: 고도화된 프롬프트로 원본 이미지 변환 렌더링
            with st.spinner("최종 3D 리모델링 화보를 렌더링 중입니다... (약 5~8초)"):
                try:
                    response = client.models.generate_content(
                        model="imagen-3.0-generate-002",
                        contents=[input_image, enhanced_prompt],
                        config=GenerateContentConfig(
                            response_modalities=[Modality.TEXT, Modality.IMAGE]
                        )
                    )

                    result_img = None
                    for part in response.candidates[0].content.parts:
                        if part.inline_data:
                            result_img = Image.open(io.BytesIO(part.inline_data.data))
                            break

                    if result_img:
                        st.session_state.rendered_image = result_img
                        st.rerun()
                    else:
                        st.error("이미지를 생성하지 못했습니다. 프롬프트나 사진을 확인해 주세요.")

                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

else:
    st.warning("⚠️ 기본 무료 시안 생성 3회가 완료되었습니다.")
    st.info("📌 **맞춤 3D 시안 및 상세 도면**은 시공사 무료 실측 상담 시 무제한 제공됩니다.")
    st.button("📞 시공사 무료 방문 실측 신청하기", type="primary")

# 시안 출력
if st.session_state.rendered_image is not None:
    st.image(st.session_state.rendered_image, caption=f"AI 리모델링 추천 렌더링 시안 ({selected_size_label})", use_container_width=True)

    buf = io.BytesIO()
    st.session_state.rendered_image.save(buf, format="PNG")
    st.download_button(
        "📥 고화질 시안 스마트폰 저장 (PNG)",
        data=buf.getvalue(),
        file_name="interior_design_render.png",
        mime="image/png"
    )

    st.caption("⚠ 본 시안은 시각적 디자인 컨셉트 참고용입니다. 실제 철거 가능 여부 및 상세 치수는 현장 실측을 통해 확정됩니다.")