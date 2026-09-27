
"""UI journeys for MiniPay, using the data-testid attributes built into
app/static/index.html specifically for stable, non-fragile selectors -
not CSS classes or visible text, which are easy to accidentally break.

Journey 1 (login) is intentionally absent: this application has no
per-user authentication in its UI (the API's X-API-Key mechanism is
service-level, not a login flow) - see ARCHITECTURE.md for that
deliberate scope decision.
"""

import re


def test_search_for_existing_transaction(page, base_url):
    """Journey: search for a transaction that exists."""
    page.goto(base_url)
    page.get_by_test_id("search-ref").fill("TXN00000029")
    page.get_by_test_id("submit-search").click()

    result = page.get_by_test_id("search-result")
    result.wait_for(state="visible")
    assert result.get_attribute("data-status") == "success"
    assert "TXN00000029" in result.inner_text()


def test_submit_payment_success(page, base_url):
    """Journey: submit a payment and validate a successful result."""
    page.goto(base_url)
    page.get_by_test_id("payment-customer-id").fill("1001")
    page.get_by_test_id("payment-amount").fill("42.50")
    page.get_by_test_id("submit-payment").click()

    result = page.get_by_test_id("payment-result")
    result.wait_for(state="visible")
    assert result.get_attribute("data-status") == "success"
    assert re.search(r"TXN[0-9A-F]+", result.inner_text())


def test_submit_payment_negative_unknown_customer(page, base_url):
    """Journey: negative/error case - a customer ID that does not exist."""
    page.goto(base_url)
    page.get_by_test_id("payment-customer-id").fill("999999999")
    page.get_by_test_id("payment-amount").fill("10.00")
    page.get_by_test_id("submit-payment").click()

    result = page.get_by_test_id("payment-result")
    result.wait_for(state="visible")
    assert result.get_attribute("data-status") == "error"
    assert "not found" in result.inner_text()


def test_search_for_nonexistent_transaction(page, base_url):
    """A second negative case: searching an unknown reference should show
    a clear error, not a silent failure or a raw exception in the console.
    """
    page.goto(base_url)
    page.get_by_test_id("search-ref").fill("TXNDOESNOTEXIST00")
    page.get_by_test_id("submit-search").click()

    result = page.get_by_test_id("search-result")
    result.wait_for(state="visible")
    assert result.get_attribute("data-status") == "error"


def test_full_journey_create_then_find(page, base_url):
    """End-to-end: create a payment through the UI, then immediately
    search for the exact reference the UI just showed us.
    """
    page.goto(base_url)
    page.get_by_test_id("payment-customer-id").fill("1001")
    page.get_by_test_id("payment-amount").fill("99.99")
    page.get_by_test_id("submit-payment").click()

    payment_result = page.get_by_test_id("payment-result")
    payment_result.wait_for(state="visible")
    match = re.search(r"(TXN[0-9A-F]+)", payment_result.inner_text())
    assert match, "expected a transaction ref in the payment result"
    new_ref = match.group(1)

    page.get_by_test_id("search-ref").fill(new_ref)
    page.get_by_test_id("submit-search").click()

    search_result = page.get_by_test_id("search-result")
    search_result.wait_for(state="visible")
    assert search_result.get_attribute("data-status") == "success"
    assert new_ref in search_result.inner_text()

