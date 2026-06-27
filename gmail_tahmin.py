import re
import json
import sys
import requests
from typing import Dict, Optional

class GmailProfileEstimatorAPI:
    def __init__(self):
        self.domain_city_fallback = {
            "gmail.com": "Mountain View, CA, USA",
            "google.com": "Mountain View, CA, USA",
            "yahoo.com": "Sunnyvale, CA, USA",
            "outlook.com": "Redmond, WA, USA",
            "icloud.com": "Cupertino, CA, USA",
            "protonmail.com": "Geneva, Switzerland",
            "hotmail.com": "Redmond, WA, USA",
            "yandex.com": "Moscow, Russia",
            "mail.ru": "Moscow, Russia",
        }

    def extract_local_part(self, email: str) -> str:
        match = re.match(r"^([^@]+)@", email.strip())
        return match.group(1) if match else ""

    def extract_domain(self, email: str) -> str:
        match = re.search(r"@([^@]+)$", email.strip())
        return match.group(1) if match else ""

    def guess_name_surname_from_api(self, first_name_candidate: str) -> Dict:
        result = {"first_name": None, "last_name": None, "gender": None, "probability": None}
        if not first_name_candidate:
            return result
        try:
            resp = requests.get(f"https://api.genderize.io/?name={first_name_candidate}", timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("gender"):
                    result["gender"] = data["gender"]
                    result["probability"] = data.get("probability")
                    result["first_name"] = data["name"].capitalize()
                else:
                    result["first_name"] = first_name_candidate.capitalize()
            else:
                result["first_name"] = first_name_candidate.capitalize()
        except Exception as e:
            result["first_name"] = first_name_candidate.capitalize()
            result["api_hata"] = str(e)
        return result

    def parse_local_parts(self, local_part: str) -> Dict:
        parts = re.split(r"[._\-]+", local_part)
        clean = [re.sub(r"\d+", "", p) for p in parts if p]
        clean = [p for p in clean if p]
        first_candidate = clean[0] if len(clean) > 0 else ""
        last_candidate = clean[1] if len(clean) > 1 else None
        return {"first_candidate": first_candidate, "last_candidate": last_candidate}

    def get_city_from_ip(self, ip_address: str = None) -> str:
        target_ip = ip_address if ip_address else ""
        try:
            url = f"http://ip-api.com/json/{target_ip}?fields=city,country,status"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    return f"{data.get('city', 'Bilinmiyor')}, {data.get('country', '')}"
        except Exception:
            pass
        return 

    def estimate(self, email: str, user_ip: str = None) -> Dict:
        local = self.extract_local_part(email)
        domain = self.extract_domain(email)
        if not local:
            return {"error": "Geçerli bir email adresi giriniz."}
        parsed = self.parse_local_parts(local)
        first_candidate = parsed["first_candidate"]
        last_candidate = parsed["last_candidate"]
        name_data = self.guess_name_surname_from_api(first_candidate)
        first_name = name_data.get("first_name")
        last_name = last_candidate.capitalize() if last_candidate else None
        city = None
        if user_ip:
            city = self.get_city_from_ip(user_ip)
        if not city or "başarısız" in city or "alınamadı" in city:
            domain_lower = domain.lower()
            for d, c in self.domain_city_fallback.items():
                if d in domain_lower:
                    city = c
                    break
            else:
                city = "Şehir tahmin edilemiyor (domain/IP bilgisi yok)"
        return {
            "email": email,
            "tahmini_ad": first_name,
            "tahmini_soyad": last_name,
            "cinsiyet_tahmini": name_data.get("gender"),
            "olasilik": name_data.get("probability"),
            "tahmini_sehir": city,
            "kullanilan_local": local,
            "domain": domain,
            "ip_kullanildi": user_ip if user_ip else "Yok (domain bazlı)"
        }

def main():
    print("\n" + "="*60)
    print("  GMAIL PROFİL TAHMİN ARACI")
    print("  GitHub: https://github.com/kadrbequit")
    print("="*60 + "\n")
    estimator = GmailProfileEstimatorAPI()
    while True:
        print("\n[1] Tek email tahmin et")
        print("[2] Birden fazla email (virgülle ayır)")
        print("[3] IP ile şehir sorgula")
        print("[4] JSON çıktı olarak kaydet")
        print("[5] Çıkış")
        secim = input("\nSeçiminiz (1-5): ").strip()
        if secim == "1":
            email = input("Email adresi girin: ").strip()
            if not email:
                print("❌ Boş giriş!")
                continue
            ip_opsiyonel = input("IP adresi girin (opsiyonel, boş bırakın): ").strip()
            ip_opsiyonel = ip_opsiyonel if ip_opsiyonel else None
            result = estimator.estimate(email, ip_opsiyonel)
            print("\n" + json.dumps(result, indent=2, ensure_ascii=False))
            print("-"*60)
        elif secim == "2":
            emails = input("Email adreslerini virgülle ayırarak girin: ").strip()
            if not emails:
                print("❌ Boş giriş!")
                continue
            email_list = [e.strip() for e in emails.split(",") if e.strip()]
            ip_opsiyonel = input("IP adresi girin (opsiyonel, tümüne uygulanır): ").strip()
            ip_opsiyonel = ip_opsiyonel if ip_opsiyonel else None
            for email in email_list:
                result = estimator.estimate(email, ip_opsiyonel)
                print("\n" + json.dumps(result, indent=2, ensure_ascii=False))
                print("-"*60)
        elif secim == "3":
            ip = input("IP adresi girin (örn: 8.8.8.8): ").strip()
            if not ip:
                print("❌ Boş IP!")
                continue
            city = estimator.get_city_from_ip(ip)
            print(f"\n📍 IP: {ip} -> Şehir: {city}")
        elif secim == "4":
            emails = input("Email adreslerini virgülle ayırarak girin: ").strip()
            if not emails:
                print("❌ Boş giriş!")
                continue
            email_list = [e.strip() for e in emails.split(",") if e.strip()]
            results = []
            for email in email_list:
                results.append(estimator.estimate(email))
            dosya_adi = input("Dosya adı (varsayılan: sonuc.json): ").strip()
            dosya_adi = dosya_adi if dosya_adi else "sonuc.json"
            with open(dosya_adi, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n✅ {len(results)} sonuç {dosya_adi} dosyasına kaydedildi.")
        elif secim == "5":
            print("\n👋 Çıkılıyor...")
            break
        else:
            print("❌ Geçersiz seçim!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Kullanıcı tarafından durduruldu.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}")
        sys.exit(1)
