# ⚙️ Cấu Hình Môi Trường

**Ngày cập nhật**: 3 Tháng 12, 2025  
**Thời gian setup**: ~10-15 phút

---

## 📋 Yêu Cầu Hệ Thống

### **Python Version**
- ✅ Python 3.8+ (khuyến nghị 3.9, 3.10, 3.11)
- ❌ Python 2.x (không hỗ trợ)
- ❌ Python < 3.8 (quá cũ)

**Kiểm tra Python:**
```bash
python --version
# Kết quả mong đợi: Python 3.8.0 hoặc cao hơn
```

### **Hệ Điều Hành**
- ✅ Linux (Ubuntu, Debian, CentOS)
- ✅ macOS (Intel, Apple Silicon)
- ✅ Windows (WSL2 khuyến nghị)

### **Internet Connection**
- ✅ Cần kết nối internet để tương tác Base Mainnet
- ✅ RPC endpoint: Được cấu hình qua biến môi trường

---

## 🚀 Bước 1: Cài Đặt Dependencies

### **Cách 1: Cài đặt từ requirements.txt**

```bash
# 1. Mở terminal và chuyển đến thư mục dự án
cd /home/dinhdat/Project1

# 2. Cài đặt tất cả dependencies
pip install -r requirements_amm.txt
```

### **Cách 2: Cài đặt từng package (nếu cách 1 lỗi)**

```bash
pip install web3==6.0.0
pip install eth-abi==4.0.0
pip install eth-keys==0.4.0
pip install requests==2.28.0
```

### **Kiểm tra cài đặt:**

```bash
python -c "import web3; print(web3.__version__)"
# Kết quả: 6.0.0 hoặc gần đó

python -c "import eth_abi; print(eth_abi.__version__)"
# Kết quả: 4.0.0 hoặc gần đó
```

---

## 🔐 Bước 2: Cấu Hình Biến Môi Trường

### **Tạo file `.env`**

```bash
# Tạo file .env ở thư mục gốc dự án
touch /home/dinhdat/Project1/.env
```

### **Nội dung file `.env`**

```env
# ====== BLOCKCHAIN RPC ======
# RPC endpoint cho Base Mainnet
RPC_URL=https://mainnet.base.org

# RPC endpoint dự phòng (optional)
RPC_URL_FALLBACK=https://base-rpc.publicnode.com

# ====== POOL CONFIGURATION ======
# Pool address ETH/USDT trên Base
POOL_ADDRESS=0x7c5e4f0c07dd9cef22c46df0e8b36a46c7ff8ef0

# Token addresses
ETH_ADDRESS=0x4200000000000000000000000000000000000006
USDT_ADDRESS=0x833589fcd6edb6e08f4c7c32d4f71b1566469c3d

# ====== SWAP PARAMETERS ======
# Mặc định swap 10,000 USDT
DEFAULT_SWAP_AMOUNT=10000

# Slippage tolerance (1% = 0.01)
SLIPPAGE_TOLERANCE=0.01

# Số scenarios orderbook: small, medium, large
ORDERBOOK_SCENARIO=medium

# ====== PERFORMANCE ======
# Phí hybrid: 30% = 0.30
HYBRID_FEE_PERCENTAGE=0.30

# Threshold filtering (basis points)
THRESHOLD_BPS=5

# ====== LOGGING ======
# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO

# Log file (optional)
LOG_FILE=/tmp/unihybrid.log
```

### **Giải Thích Các Biến**

| Biến | Ý Nghĩa | Ví Dụ |
|------|---------|-------|
| `RPC_URL` | Kết nối blockchain | https://mainnet.base.org |
| `POOL_ADDRESS` | Địa chỉ pool Uniswap V3 | 0x7c5e... |
| `ETH_ADDRESS` | Địa chỉ token ETH | 0x4200... |
| `USDT_ADDRESS` | Địa chỉ token USDT | 0x8335... |
| `DEFAULT_SWAP_AMOUNT` | Số lượng mặc định (USDT) | 10000 |
| `SLIPPAGE_TOLERANCE` | Chấp nhận slippage | 0.01 (1%) |
| `ORDERBOOK_SCENARIO` | Loại orderbook | medium |
| `HYBRID_FEE_PERCENTAGE` | % phí UniHybrid | 0.30 (30%) |
| `THRESHOLD_BPS` | Ngưỡng lọc | 5 bps |

---

## 🔍 Bước 3: Kiểm Tra Cài Đặt

### **Test 1: Kiểm tra Python**

```bash
python --version
```

**Kết quả mong đợi:**
```
Python 3.8.0 (hoặc 3.9.x, 3.10.x, 3.11.x)
```

### **Test 2: Kiểm tra web3.py**

```bash
python -c "from web3 import Web3; print('✅ web3.py cài đặt thành công')"
```

**Kết quả mong đợi:**
```
✅ web3.py cài đặt thành công
```

### **Test 3: Kiểm tra eth_abi**

```bash
python -c "from eth_abi import decode; print('✅ eth_abi cài đặt thành công')"
```

**Kết quả mong đợi:**
```
✅ eth_abi cài đặt thành công
```

### **Test 4: Kiểm tra kết nối RPC**

```python
from web3 import Web3

# Kết nối RPC
w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))

# Kiểm tra kết nối
if w3.is_connected():
    print("✅ Kết nối RPC thành công")
    print(f"   Chain ID: {w3.eth.chain_id}")
    print(f"   Block hiện tại: {w3.eth.block_number}")
else:
    print("❌ Không thể kết nối RPC")
    print("   Kiểm tra lại RPC_URL trong file .env")
```

**Chạy:**
```bash
python test_rpc_connection.py
```

**Kết quả mong đợi:**
```
✅ Kết nối RPC thành công
   Chain ID: 8453
   Block hiện tại: 15234567
```

### **Test 5: Kiểm tra file .env được load**

```python
import os
from dotenv import load_dotenv

load_dotenv('/home/dinhdat/Project1/.env')

pool_address = os.getenv('POOL_ADDRESS')
swap_amount = os.getenv('DEFAULT_SWAP_AMOUNT')

if pool_address and swap_amount:
    print("✅ File .env được load thành công")
    print(f"   Pool: {pool_address}")
    print(f"   Swap amount: {swap_amount}")
else:
    print("❌ File .env không được load")
    print("   Kiểm tra lại file .env")
```

---

## 🚨 Troubleshooting

### **Lỗi 1: "No module named 'web3'"**

**Nguyên nhân**: web3.py chưa được cài đặt

**Cách khắc phục**:
```bash
pip install web3==6.0.0
```

### **Lỗi 2: "No module named 'eth_abi'"**

**Nguyên nhân**: eth_abi chưa được cài đặt

**Cách khắc phục**:
```bash
pip install eth-abi==4.0.0
```

### **Lỗi 3: "HTTPConnectionPool(host='mainnet.base.org')"**

**Nguyên nhân**: Không thể kết nối RPC endpoint

**Cách khắc phục**:
1. Kiểm tra internet connection
2. Thử RPC endpoint khác:
   ```env
   RPC_URL=https://base-rpc.publicnode.com
   ```
3. Kiểm tra firewall

### **Lỗi 4: "Module 'dotenv' not found"**

**Nguyên nhân**: python-dotenv chưa cài đặt

**Cách khắc phục**:
```bash
pip install python-dotenv
```

### **Lỗi 5: ".env file not found"**

**Nguyên nhân**: File .env không tồn tại hoặc đặt sai vị trí

**Cách khắc phục**:
```bash
# Kiểm tra file .env có tồn tại không
ls -la /home/dinhdat/Project1/.env

# Nếu không có, tạo file mới
touch /home/dinhdat/Project1/.env

# Thêm nội dung vào file
cat >> /home/dinhdat/Project1/.env << EOF
RPC_URL=https://mainnet.base.org
POOL_ADDRESS=0x7c5e4f0c07dd9cef22c46df0e8b36a46c7ff8ef0
ETH_ADDRESS=0x4200000000000000000000000000000000000006
USDT_ADDRESS=0x833589fcd6edb6e08f4c7c32d4f71b1566469c3d
DEFAULT_SWAP_AMOUNT=10000
SLIPPAGE_TOLERANCE=0.01
ORDERBOOK_SCENARIO=medium
HYBRID_FEE_PERCENTAGE=0.30
THRESHOLD_BPS=5
LOG_LEVEL=INFO
EOF
```

### **Lỗi 6: "BadStatusLine" hoặc "ConnectionError"**

**Nguyên nhân**: RPC endpoint bị giới hạn tốc độ (rate limit)

**Cách khắc phục**:
```bash
# Thử dùng RPC endpoint khác
# Trong file .env, thay đổi:
RPC_URL=https://base-rpc.publicnode.com
# hoặc
RPC_URL=https://rpc.ankr.com/base
```

---

## ✅ Kiểm Tra Hoàn Chỉnh

Chạy script kiểm tra toàn bộ:

```bash
cat > /tmp/check_setup.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
from pathlib import Path

def check_python_version():
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python quá cũ: {version.major}.{version.minor}")
        return False

def check_packages():
    packages = ['web3', 'eth_abi', 'decimal', 'requests']
    all_ok = True
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"✅ {pkg} đã cài đặt")
        except ImportError:
            print(f"❌ {pkg} chưa cài đặt")
            all_ok = False
    return all_ok

def check_env_file():
    env_path = Path('/home/dinhdat/Project1/.env')
    if env_path.exists():
        print(f"✅ File .env tồn tại")
        
        # Kiểm tra các biến quan trọng
        with open(env_path) as f:
            content = f.read()
            required = ['RPC_URL', 'POOL_ADDRESS', 'DEFAULT_SWAP_AMOUNT']
            for var in required:
                if var in content:
                    print(f"   ✅ {var} được định nghĩa")
                else:
                    print(f"   ❌ {var} không được định nghĩa")
        return True
    else:
        print(f"❌ File .env không tồn tại")
        return False

def main():
    print("🔍 Kiểm tra cấu hình môi trường...\n")
    
    results = []
    results.append(("Python version", check_python_version()))
    print()
    results.append(("Packages", check_packages()))
    print()
    results.append((".env file", check_env_file()))
    
    print("\n" + "="*50)
    if all(r[1] for r in results):
        print("✅ Tất cả kiểm tra đều OK!")
        print("   Sẵn sàng chạy modules")
    else:
        print("❌ Có lỗi, vui lòng khắc phục trên")

if __name__ == '__main__':
    main()
EOF

python /tmp/check_setup.py
```

---

## 📚 Tài Liệu Tiếp Theo

Sau khi setup xong:

1. **02_TỔNG_QUAN_CÁC_MODULE.md** - Hiểu flow hoàn chỉnh
2. **03_HƯỚNG_DẪN_TEST.md** - Chạy test để kiểm tra
3. **04_MODULE1_CHI_TIẾT.md** - Bắt đầu học Module 1

---

## 💡 Mẹo Hữu Ích

### **Sử dụng Virtual Environment (khuyến nghị)**

```bash
# Tạo virtual environment
python3 -m venv /home/dinhdat/Project1/.venv

# Kích hoạt
source /home/dinhdat/Project1/.venv/bin/activate  # Linux/macOS
# hoặc
/home/dinhdat/Project1/.venv\Scripts\activate     # Windows

# Cài đặt dependencies
pip install -r requirements_amm.txt

# Kiểm tra
python --version
```

### **Dùng Conda (nếu có)**

```bash
# Tạo environment
conda create -n unihybrid python=3.10

# Kích hoạt
conda activate unihybrid

# Cài đặt
pip install -r requirements_amm.txt
```

### **Cập Nhật Packages**

```bash
# Nếu có phiên bản cũ
pip install --upgrade web3 eth-abi
```

---

## ✨ Hoàn Tất Setup!

Nếu tất cả kiểm tra đều ✅, bạn đã sẵn sàng!

**Bước tiếp theo:**
→ Đọc **02_TỔNG_QUAN_CÁC_MODULE.md** để hiểu flow hoàn chỉnh

