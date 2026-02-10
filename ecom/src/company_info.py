"""公司信息收集模块 - 股价、市值、财报"""
from datetime import datetime

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("Warning: yfinance not installed. Run: pip install yfinance")


class CompanyInfo:
    """收集关键公司的股价和财务信息"""

    # 公司配置
    COMPANIES = {
        'Amazon': {
            'symbol': 'AMZN',
            'name': 'Amazon.com Inc.',
            'sector': 'Consumer Cyclical',
            'industry': 'Internet Retail',
        },
        # 可以添加更多上市公司
        # 'Shopify': {
        #     'symbol': 'SHOP',
        #     'name': 'Shopify Inc.',
        #     'sector': 'Technology',
        #     'industry': 'Software - Application',
        # },
    }

    def __init__(self):
        pass

    def get_company_info(self, company_name):
        """获取指定公司的完整信息"""
        if not YFINANCE_AVAILABLE:
            return None

        config = self.COMPANIES.get(company_name)
        if not config:
            return None

        symbol = config.get('symbol')
        if not symbol:
            return {
                'name': config['name'],
                'symbol': None,
                'is_public': False,
            }

        print(f"正在获取 {company_name} ({symbol}) 公司信息...")

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # 股票信息
            current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            prev_close = info.get('previousClose', 0)
            change = current_price - prev_close if current_price and prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0

            market_cap = info.get('marketCap', 0)

            return {
                'name': config['name'],
                'symbol': symbol,
                'sector': config['sector'],
                'industry': config['industry'],
                'is_public': True,
                'stock': {
                    'symbol': symbol,
                    'price': current_price,
                    'prev_close': prev_close,
                    'change': change,
                    'change_pct': change_pct,
                    'market_cap': market_cap,
                    'market_cap_str': self._format_number(market_cap),
                    'volume': info.get('volume', 0),
                    'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
                    'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
                    'currency': info.get('currency', 'USD'),
                    'exchange': info.get('exchange', ''),
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                },
                'financials': {
                    'total_revenue': info.get('totalRevenue', 0),
                    'total_revenue_str': self._format_number(info.get('totalRevenue', 0)),
                    'profit_margin': info.get('profitMargins', 0),
                    'operating_margin': info.get('operatingMargins', 0),
                    'pe_ratio': info.get('trailingPE', 0),
                    'forward_pe': info.get('forwardPE', 0),
                    'eps': info.get('trailingEps', 0),
                    'target_price': info.get('targetMeanPrice', 0),
                    'recommendation': info.get('recommendationKey', ''),
                    'analyst_count': info.get('numberOfAnalystOpinions', 0),
                },
            }

        except Exception as e:
            print(f"  获取 {company_name} 信息失败: {e}")
            return None

    def get_all_companies_info(self):
        """获取所有关键公司的信息"""
        results = {}
        for company_name in self.COMPANIES:
            info = self.get_company_info(company_name)
            if info:
                results[company_name] = info
        return results

    def _format_number(self, value):
        """格式化数字为可读字符串"""
        if not value:
            return 'N/A'

        if value >= 1e12:
            return f"${value/1e12:.2f}T"
        elif value >= 1e9:
            return f"${value/1e9:.2f}B"
        elif value >= 1e6:
            return f"${value/1e6:.2f}M"
        else:
            return f"${value:,.0f}"


def format_company_info_html(companies_info):
    """生成公司信息 HTML 卡片"""
    if not companies_info:
        return ""

    html_parts = []

    for company_name, info in companies_info.items():
        if not info.get('is_public') or not info.get('stock'):
            continue

        stock = info['stock']
        financials = info.get('financials', {}) or {}

        # 涨跌颜色
        change_pct = stock.get('change_pct', 0)
        if change_pct > 0:
            change_color = '#22c55e'  # 绿色
            change_icon = '▲'
            change_bg = 'rgba(34, 197, 94, 0.1)'
        elif change_pct < 0:
            change_color = '#ef4444'  # 红色
            change_icon = '▼'
            change_bg = 'rgba(239, 68, 68, 0.1)'
        else:
            change_color = '#6b7280'
            change_icon = '—'
            change_bg = 'rgba(107, 114, 128, 0.1)'

        # 推荐评级颜色
        rec = financials.get('recommendation', '').lower()
        rec_colors = {
            'strong_buy': '#22c55e',
            'buy': '#84cc16',
            'hold': '#f59e0b',
            'sell': '#ef4444',
            'strong_sell': '#dc2626',
        }
        rec_color = rec_colors.get(rec, '#6b7280')
        rec_text = rec.replace('_', ' ').title() if rec else 'N/A'

        # 利润率格式化
        profit_margin = financials.get('profit_margin', 0)
        profit_margin_str = f"{profit_margin*100:.1f}%" if profit_margin else 'N/A'

        # PE 比率
        pe_ratio = financials.get('pe_ratio', 0)
        pe_str = f"{pe_ratio:.1f}" if pe_ratio else 'N/A'

        card_html = f'''
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 12px; padding: 20px; margin-bottom: 16px; border: 1px solid #334155;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px;">
                <div>
                    <div style="font-size: 18px; font-weight: 600; color: #f1f5f9;">{company_name}</div>
                    <div style="font-size: 13px; color: #94a3b8;">{stock.get('symbol', '')} · {info.get('industry', '')}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 24px; font-weight: 700; color: #f1f5f9;">${stock.get('price', 0):,.2f}</div>
                    <div style="font-size: 14px; color: {change_color}; background: {change_bg}; padding: 2px 8px; border-radius: 4px; display: inline-block;">
                        {change_icon} {abs(change_pct):.2f}%
                    </div>
                </div>
            </div>

            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px 0 0 8px; width: 25%;">
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">市值</div>
                        <div style="font-size: 15px; font-weight: 600; color: #e2e8f0;">{stock.get('market_cap_str', 'N/A')}</div>
                    </td>
                    <td style="background: rgba(255,255,255,0.05); padding: 12px; width: 25%;">
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">年营收</div>
                        <div style="font-size: 15px; font-weight: 600; color: #e2e8f0;">{financials.get('total_revenue_str', 'N/A')}</div>
                    </td>
                    <td style="background: rgba(255,255,255,0.05); padding: 12px; width: 25%;">
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">利润率</div>
                        <div style="font-size: 15px; font-weight: 600; color: #e2e8f0;">{profit_margin_str}</div>
                    </td>
                    <td style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 0 8px 8px 0; width: 25%;">
                        <div style="font-size: 11px; color: #64748b; text-transform: uppercase;">P/E</div>
                        <div style="font-size: 15px; font-weight: 600; color: #e2e8f0;">{pe_str}</div>
                    </td>
                </tr>
            </table>

            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #334155; display: flex; justify-content: space-between; font-size: 12px; color: #64748b;">
                <span>52周: ${stock.get('fifty_two_week_low', 0):,.2f} - ${stock.get('fifty_two_week_high', 0):,.2f}</span>
                <span style="color: {rec_color};">分析师评级: {rec_text}</span>
            </div>
        </div>
        '''

        html_parts.append(card_html)

    if not html_parts:
        return ""

    return f'''
    <div style="margin-bottom: 24px;">
        <h2 style="color: #f1f5f9; font-size: 18px; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #3b82f6;">
            📊 关键企业动态
        </h2>
        {''.join(html_parts)}
    </div>
    '''


if __name__ == '__main__':
    # 测试
    ci = CompanyInfo()
    info = ci.get_all_companies_info()

    for company, data in info.items():
        print(f"\n=== {company} ===")
        if data.get('stock'):
            stock = data['stock']
            print(f"  价格: ${stock['price']:,.2f}")
            print(f"  涨跌: {stock['change_pct']:+.2f}%")
            print(f"  市值: {stock['market_cap_str']}")

        if data.get('financials'):
            fin = data['financials']
            print(f"  营收: {fin.get('total_revenue_str', 'N/A')}")
            pm = fin.get('profit_margin', 0)
            print(f"  利润率: {pm*100:.1f}%" if pm else "  利润率: N/A")
            print(f"  P/E: {fin.get('pe_ratio', 'N/A')}")
            print(f"  评级: {fin.get('recommendation', 'N/A')}")

    # 测试 HTML 输出
    print("\n=== HTML Preview ===")
    html = format_company_info_html(info)
    print(f"HTML length: {len(html)} chars")
