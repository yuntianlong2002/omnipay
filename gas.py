from flask import Flask, jsonify
from flask_caching import Cache
import requests
from base64 import b64encode
from time import sleep

app = Flask(__name__)
# Configure Flask-Caching
app.config['CACHE_TYPE'] = 'simple'
cache = Cache(app)
cache.init_app(app)

# Prepare the authentication
infura_api_key = ""
infura_api_key_secret = ""
auth_value = b64encode(f"{infura_api_key}:{infura_api_key_secret}".encode()).decode()

# Supported chains mapping to their Chain ID and ticker for price fetching
supported_chains = {
    # "Arbitrum": {"chain_id": 42161, "ticker": "ETH"},
    "Avalanche": {"chain_id": 43114, "ticker": "AVAX"},
    "BNB Chain": {"chain_id": 56, "ticker": "BNB"},
    # "Cronos": {"chain_id": 25, "ticker": "CRO"},
    # "Ethereum": {"chain_id": 1, "ticker": "ETH"},
    "Optimism": {"chain_id": 10, "ticker": "ETH"},
}

def get_suggested_gas_fees(chain_id):
    url = f"https://gas.api.infura.io/networks/{chain_id}/suggestedGasFees"
    headers = {'Authorization': f'Basic {auth_value}'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")
    return None

@cache.memoize(timeout=60)  # Cache the result for 1 minute
def get_currency_price_usd_cached(ticker):
    # Placeholder for actual URL, replace https://cryptoprices.cc/{ticker} with the real API endpoint if necessary
    url = f"https://cryptoprices.cc/{ticker}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        # Directly return the response content as a float
        return float(response.text)
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")
    return None

def calculate_gas_cost_in_usd(gas_fee_gwei, currency_price_usd, gas_used=65000):
    gas_fee_currency = gas_fee_gwei * gas_used / 1e9
    total_cost_usd = gas_fee_currency * currency_price_usd
    return total_cost_usd

@app.route('/gas-costs')
def get_gas_costs():
    results = {}
    for chain_name, info in supported_chains.items():
        sleep(1)  # Sleep 1 second between each API call to avoid rate limits
        chain_id = info['chain_id']
        ticker = info['ticker']
        gas_fees = get_suggested_gas_fees(chain_id)
        if gas_fees:
            medium_gas_fee_gwei = float(gas_fees['medium']['suggestedMaxFeePerGas'])
            currency_price_usd = get_currency_price_usd_cached(ticker)
            if currency_price_usd is not None:
                total_cost_usd = calculate_gas_cost_in_usd(medium_gas_fee_gwei, currency_price_usd)
                results[chain_name] = {"Total medium gas cost in USD (for 21000 gas used)": total_cost_usd}
            else:
                results[chain_name] = "Could not fetch the current price in USD."
        else:
            results[chain_name] = "Could not fetch suggested gas fees."
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)