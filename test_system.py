"""
Comprehensive automated test suite for the AQI-Based Plant Recommender system.
Verifies model inference, schema integrity, API handlers, AQI math, and dashboard callbacks.
"""
import asyncio
import os
import sys

# Ensure UTF-8 console output
sys.stdout.reconfigure(encoding="utf-8")

def run_tests():
    print("=" * 60)
    print("🧪 RUNNING AQI-PLANT-RECOMMENDER SYSTEM TESTS")
    print("=" * 60)
    passed = 0
    total = 0

    # 1. Test Model & Predictor
    total += 1
    print("\n[Test 1] Testing ML Predictor & MultiLabelBinarizer...")
    try:
        from app.predictor import predict_plants, mlb, model
        assert model is not None, "Model is None"
        assert mlb is not None, "MLB is None"
        assert len(mlb.classes_) == 12, f"Expected 12 plant classes, got {len(mlb.classes_)}"

        sample = {
            "PM2.5": 55.0, "PM10": 95.0, "NO": 18.0, "NO2": 28.0, "NOx": 46.0,
            "NH3": 14.0, "CO": 2.1, "SO2": 9.0, "O3": 24.0,
            "Benzene": 2.2, "Toluene": 9.5, "Xylene": 3.8, "AQI": 145.0
        }
        res = predict_plants(sample)
        assert "recommendations" in res, "Missing 'recommendations' key"
        assert "all_predictions" in res, "Missing 'all_predictions' key"
        assert len(res["recommendations"]) == 3, f"Expected 3 recommendations, got {len(res['recommendations'])}"
        assert len(res["all_predictions"]) == 12, f"Expected 12 predictions, got {len(res['all_predictions'])}"
        for item in res["recommendations"]:
            assert 0.0 <= item["confidence"] <= 1.0, f"Confidence out of bounds: {item['confidence']}"
            assert isinstance(item["plant"], str), f"Plant is not str: {item['plant']}"

        print(f"  ✅ Predictor passed. Top plant: {res['recommendations'][0]['plant']} ({res['recommendations'][0]['confidence']*100:.1f}%)")
        passed += 1
    except Exception as e:
        print(f"  ❌ Test 1 failed: {e}")

    # 2. Test Feature Normalization (PM2_5 alias support)
    total += 1
    print("\n[Test 2] Testing PM2_5 alias key normalization...")
    try:
        sample_alias = {
            "PM2_5": 55.0, "PM10": 95.0, "NO": 18.0, "NO2": 28.0, "NOx": 46.0,
            "NH3": 14.0, "CO": 2.1, "SO2": 9.0, "O3": 24.0,
            "Benzene": 2.2, "Toluene": 9.5, "Xylene": 3.8, "AQI": 145.0
        }
        res_alias = predict_plants(sample_alias)
        assert len(res_alias["recommendations"]) == 3
        print("  ✅ Feature key normalization (PM2_5 -> PM2.5) passed.")
        passed += 1
    except Exception as e:
        print(f"  ❌ Test 2 failed: {e}")

    # 3. Test FastAPI Schema and Handlers
    total += 1
    print("\n[Test 3] Testing FastAPI app handlers...")
    try:
        from app.main import root, health_check, predict
        from app.data import Data

        r_root = root()
        assert r_root["status"] == "online"
        r_health = health_check()
        assert r_health["status"] == "healthy"

        d = Data(**sample)
        r_predict = asyncio.run(predict(d))
        assert "recommendations" in r_predict
        assert "all_predictions" in r_predict
        assert "top_3_plants" in r_predict
        assert len(r_predict["recommendations"]) == 3
        print("  ✅ FastAPI endpoints (root, health, predict) passed.")
        passed += 1
    except Exception as e:
        print(f"  ❌ Test 3 failed: {e}")

    # 4. Test India AQI Breakpoint Math
    total += 1
    print("\n[Test 4] Testing India AQI breakpoint calculations...")
    try:
        import dash_aqi
        # Good range
        assert dash_aqi.calculate_india_aqi(20, 30) == 33
        # Satisfactory range
        assert dash_aqi.calculate_india_aqi(50, 75) == 83
        # Category strings and hex colors
        cat_good, col_good = dash_aqi.get_aqi_category(40)
        assert "Good" in cat_good and col_good == "#2d6a4f"
        cat_mod, col_mod = dash_aqi.get_aqi_category(150)
        assert "Moderate" in cat_mod
        print("  ✅ AQI calculation and category color mapping passed.")
        passed += 1
    except Exception as e:
        print(f"  ❌ Test 4 failed: {e}")

    # 5. Test Live OpenWeatherMap API Connectivity
    total += 1
    print("\n[Test 5] Testing OpenWeatherMap API connectivity...")
    try:
        owm_res = dash_aqi.fetch_from_openweather(28.6139, 77.2090, "Delhi, IN", "OpenWeather")
        assert len(owm_res) == 15, f"Expected 15 elements in fetch tuple, got {len(owm_res)}"
        pm25_val = owm_res[0]
        aqi_val = owm_res[12]
        location_str = owm_res[13]
        assert pm25_val is not None, "PM2.5 value is None"
        assert aqi_val is not None, "AQI value is None"
        assert "Delhi" in location_str
        print(f"  ✅ OpenWeatherMap live fetch passed (PM2.5: {pm25_val}, AQI: {aqi_val}).")
        passed += 1
    except Exception as e:
        print(f"  ❌ Test 5 failed: {e}")

    # 6. Test Dash Prediction UI Callback
    total += 1
    print("\n[Test 6] Testing Dash prediction callback rendering...")
    try:
        output_card, fig_top3, fig_all = dash_aqi.get_predictions(
            n_clicks=1,
            pm2_5=60.0, pm10=110.0, no=22.0, no2=35.0, nox=57.0,
            nh3=18.0, co=2.2, so2=12.0, o3=28.0,
            benzene=3.0, toluene=12.0, xylene=5.0, aqi=160.0
        )
        assert output_card is not None
        assert len(fig_top3.data) > 0, "Top 3 figure has no data traces"
        assert len(fig_all.data) > 0, "All predictions figure has no data traces"
        print("  ✅ Dash UI callback generated recommendation card and 2 Plotly figures successfully.")
        passed += 1
    except Exception as e:
        print(f"  ❌ Test 6 failed: {e}")

    # 7. Test Empty Input Validation
    total += 1
    print("\n[Test 7] Testing empty input validation guard...")
    try:
        warn_card, fig_empty1, fig_empty2 = dash_aqi.get_predictions(
            n_clicks=1,
            pm2_5=None, pm10=None, no=None, no2=None, nox=None,
            nh3=None, co=None, so2=None, o3=None,
            benzene=None, toluene=None, xylene=None, aqi=None
        )
        assert "Please fetch or manually enter" in str(warn_card)
        print("  ✅ Empty input validation guard passed.")
        passed += 1
    except Exception as e:
        print(f"  ❌ Test 7 failed: {e}")

    print("\n" + "=" * 60)
    print(f"📊 SUMMARY: {passed}/{total} tests passed.")
    print("=" * 60)
    return passed == total

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
