import requests

BASE_URL = "http://localhost:8001"


def test_endpoint(name, method, path, headers, body=None):
    url = f"{BASE_URL}{path}"
    print(f"Testing {name}...")
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        else:
            response = requests.post(url, headers=headers, json=body)

        print(f"  URL: {url}")
        print(f"  Status: {response.status_code}")
        if response.status_code != 200 and response.status_code != 403:
            print(f"  Response: {response.text[:200]}")
        return response.status_code
    except Exception as e:
        print(f"  Error: {e}")
        return None


def run_tests():
    # 1. Authorized Access
    headers_ok = {"X-Tenant-ID": "acme-corp"}
    test_endpoint(
        "Authorized Chunks", "GET", "/chunks/source/acme-corp/test/doc1", headers_ok
    )

    # 2. Blocked Cross-Tenant Access
    headers_attacker = {"X-Tenant-ID": "attacker-tenant"}
    status = test_endpoint(
        "Cross-Tenant Chunks (Blocked)",
        "GET",
        "/chunks/source/acme-corp/test/doc1",
        headers_attacker,
    )
    if status == 403:
        print("✅ SUCCESS: Cross-tenant access blocked with 403.")
    else:
        print(f"❌ FAILURE: Expected 403, got {status}")

    # 3. Verify Search with Body Payload
    search_payload = {"query": "test", "tenant_id": "acme-corp"}
    test_endpoint("Authorized Search", "POST", "/search", headers_ok, search_payload)

    status_search = test_endpoint(
        "Cross-Tenant Search (Blocked)",
        "POST",
        "/search",
        headers_attacker,
        search_payload,
    )
    if status_search == 403:
        print("✅ SUCCESS: Cross-tenant search blocked with 403.")
    else:
        print(f"❌ FAILURE: Expected 403, got {status_search}")


if __name__ == "__main__":
    run_tests()
