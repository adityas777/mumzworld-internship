"""
sample_data.py - Realistic product review datasets for testing.
Covers the full spectrum: positive, negative, mixed, contradictory, spam, sparse, multilingual.
"""

# ---------------------------------------------------------------------------
# Dataset definitions
# Each entry: {"name": str, "product": str, "reviews": [str]}
# ---------------------------------------------------------------------------

DATASETS: dict[str, dict] = {

    # ── 1. Strongly positive ────────────────────────────────────────────────
    "positive_stroller": {
        "product": "Bugaboo Fox 3 Stroller",
        "reviews": [
            "Absolutely love this stroller! So smooth on all terrains.",
            "Best purchase I made for my baby. The suspension is incredible.",
            "Very easy to fold and fits in my car trunk without any hassle.",
            "My baby falls asleep every time we go for a walk — so comfortable.",
            "Worth every penny. Build quality is top notch.",
            "The canopy is huge and protects from sun perfectly.",
            "Steering is effortless even with one hand.",
            "We've used it for 2 years and it still looks brand new.",
            "Customer service was great when I had a question about assembly.",
            "Highly recommend to any new mom. Life changing product.",
            "The seat reclines fully flat which is perfect for newborns.",
            "Looks stylish and gets compliments everywhere we go.",
        ],
    },

    # ── 2. Strongly negative ────────────────────────────────────────────────
    "negative_formula": {
        "product": "Generic Baby Formula Brand X",
        "reviews": [
            "My baby refused to drink this after the first bottle.",
            "Caused terrible gas and bloating. Had to switch immediately.",
            "The powder doesn't dissolve properly — always lumpy.",
            "Smell is very off-putting, not like other formulas.",
            "My pediatrician told me to stop using it after my baby had a reaction.",
            "Packaging is misleading — the scoop size changed without notice.",
            "Gave my baby constipation for 3 days straight.",
            "Returned it after one use. Complete waste of money.",
            "The tin lid doesn't seal properly, worried about contamination.",
            "Would not recommend to any parent. Stick to trusted brands.",
            "My baby lost weight while on this formula. Switched and she recovered.",
            "Terrible product. Never buying again.",
        ],
    },

    # ── 3. Mixed sentiment ──────────────────────────────────────────────────
    "mixed_car_seat": {
        "product": "Joie i-Spin 360 Car Seat",
        "reviews": [
            "The 360 rotation is a game changer for getting baby in and out.",
            "Installation was confusing — took me 2 hours to figure out.",
            "Very safe feeling once installed correctly.",
            "Quite bulky, takes up a lot of space in a small car.",
            "My baby seems comfortable and doesn't fuss during long drives.",
            "The harness is a bit tricky to adjust.",
            "Love the extended rear-facing option.",
            "Expensive but worth it for the safety features.",
            "The cup holder broke after 3 months.",
            "Instructions could be much clearer.",
            "Great product overall despite the learning curve.",
            "Padding is very soft and my toddler loves sitting in it.",
        ],
    },

    # ── 4. Contradictory reviews ────────────────────────────────────────────
    "contradictory_monitor": {
        "product": "Infant Optics DXR-8 Baby Monitor",
        "reviews": [
            "Crystal clear video quality, I can see every detail.",
            "The video is grainy and pixelated at night.",
            "Battery lasts all night without charging.",
            "Battery dies after 3 hours, very disappointing.",
            "Range is excellent — works throughout our whole house.",
            "Signal drops constantly even in the next room.",
            "Very easy to set up, took 5 minutes.",
            "Setup was a nightmare, spent hours on the phone with support.",
            "The two-way audio is clear and my baby responds to my voice.",
            "Audio has terrible static, can barely hear anything.",
            "Temperature sensor is accurate and useful.",
            "Temperature readings are always wrong.",
        ],
    },

    # ── 5. Spam / noisy input ───────────────────────────────────────────────
    "spam_noisy": {
        "product": "Random Baby Toy",
        "reviews": [
            "BEST PRODUCT EVER!!!!!!! BUY NOW!!!!! 5 STARS!!!!!",
            "aaaaaaaaa",
            ".",
            "Visit www.cheapdeals.xyz for discount codes!!!",
            "I bought this as a gift",
            "ok",
            "seller contacted me to leave 5 stars so here it is",
            "not what i expected",
            "my friend recommended it",
            "   ",
            "1",
            "good",
            "bad",
            "meh",
            "This is a paid review. Product was given for free.",
        ],
    },

    # ── 6. Very few reviews ─────────────────────────────────────────────────
    "sparse_reviews": {
        "product": "Organic Teething Biscuits",
        "reviews": [
            "My baby loved these!",
            "Seemed okay but not sure if worth the price.",
        ],
    },

    # ── 7. Missing key product info ─────────────────────────────────────────
    "vague_reviews": {
        "product": "Unknown Baby Product",
        "reviews": [
            "It arrived on time.",
            "Packaging was nice.",
            "Looks good.",
            "Seems fine.",
            "Will update after using it more.",
            "Delivery was fast.",
            "Haven't tried it yet but looks promising.",
            "The box was damaged but the product inside was okay.",
        ],
    },

    # ── 8. Arabic + English mixed ───────────────────────────────────────────
    "multilingual_diapers": {
        "product": "Pampers Premium Care Diapers",
        "reviews": [
            "الحفاضات ممتازة جداً، ما تسرب أبداً حتى في الليل.",
            "Best diapers I've ever used for my newborn.",
            "جودة عالية وسعر معقول مقارنة بالماركات الثانية.",
            "No leaks overnight, my baby sleeps comfortably.",
            "الحجم مناسب تماماً لعمر طفلي.",
            "Soft on baby's skin, no rashes at all.",
            "اشتريتها من موقع مامز وورلد وجاءت بسرعة.",
            "Great absorbency, highly recommend for sensitive skin.",
            "ما عندي أي شكوى، منتج ممتاز.",
            "The tabs are strong and don't come undone.",
            "أفضل حفاضات جربتها لحد الآن.",
            "Very good quality for the price.",
        ],
    },

    # ── 9. Single dominant issue ────────────────────────────────────────────
    "sizing_issue_shoes": {
        "product": "Baby Stride First Walker Shoes",
        "reviews": [
            "Cute shoes but runs very small — order 2 sizes up!",
            "Adorable design but the sizing is completely off.",
            "My baby's feet couldn't fit even though I ordered the right size.",
            "Love the look but had to return for a bigger size.",
            "Quality is good but size chart is inaccurate.",
            "Returned twice because of sizing issues.",
            "Finally got the right size after ordering 2 sizes up — now love them!",
            "The material is soft but please fix the sizing.",
            "Would give 5 stars if the sizing was correct.",
            "Sizing runs at least 1.5 sizes small. Be warned.",
        ],
    },

    # ── 10. Safety concern reviews ──────────────────────────────────────────
    "safety_concern_toy": {
        "product": "Colorful Stacking Rings Toy",
        "reviews": [
            "The paint started chipping after one week — worried about my baby ingesting it.",
            "Small parts came loose, potential choking hazard.",
            "Returned immediately after noticing the paint peeling.",
            "Not safe for babies under 3 — the rings break apart too easily.",
            "My baby put it in her mouth and the color came off on her tongue.",
            "Looks nice but the quality is dangerous for infants.",
            "Do not buy if your child is still mouthing toys.",
            "Reported to the store — this should be recalled.",
            "The plastic smells strongly of chemicals.",
            "Bought for my 8-month-old and immediately threw it away after seeing the paint chip.",
        ],
    },
}
