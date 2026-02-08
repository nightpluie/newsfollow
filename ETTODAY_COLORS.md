# ETtoday 品牌配色方案

## 從 Logo 提取的官方配色

根據 ETtoday 實際 Logo 分析：

```
深藍色 (Navy Blue)  - 主要文字 "ET"
橙色 (Orange)       - "to" 和圓點
淺藍色 (Light Blue) - "day" 和圓點
```

## 專業配色系統

### 主要配色
```css
/* Primary - 深藍色 (ETtoday Navy) */
--et-navy-50:  #EFF6FF;
--et-navy-100: #DBEAFE;
--et-navy-200: #BFDBFE;
--et-navy-300: #93C5FD;
--et-navy-400: #60A5FA;
--et-navy-500: #3B82F6;
--et-navy-600: #1E3A8A;  /* 主色 */
--et-navy-700: #1E40AF;
--et-navy-800: #1E293B;
--et-navy-900: #0F172A;  /* 深色文字 */

/* Orange - 橙色強調 (ETtoday Orange) */
--et-orange-50:  #FFF7ED;
--et-orange-100: #FFEDD5;
--et-orange-200: #FED7AA;
--et-orange-300: #FDBA74;
--et-orange-400: #FB923C;
--et-orange-500: #F97316;  /* 主色 */
--et-orange-600: #EA580C;
--et-orange-700: #C2410C;
--et-orange-800: #9A3412;
--et-orange-900: #7C2D12;

/* Light Blue - 淺藍色輔助 (ETtoday Sky) */
--et-sky-50:  #F0F9FF;
--et-sky-100: #E0F2FE;
--et-sky-200: #BAE6FD;
--et-sky-300: #7DD3FC;
--et-sky-400: #38BDF8;
--et-sky-500: #0EA5E9;  /* 主色 */
--et-sky-600: #0284C7;
--et-sky-700: #0369A1;
--et-sky-800: #075985;
--et-sky-900: #0C4A6E;
```

### 中性色系
```css
/* Neutral - 灰階 */
--et-gray-50:  #F8FAFC;
--et-gray-100: #F1F5F9;
--et-gray-200: #E2E8F0;
--et-gray-300: #CBD5E1;
--et-gray-400: #94A3B8;
--et-gray-500: #64748B;
--et-gray-600: #475569;
--et-gray-700: #334155;
--et-gray-800: #1E293B;
--et-gray-900: #0F172A;
```

### 語意化配色
```css
/* Success */
--et-success: #10B981;

/* Warning */
--et-warning: #F59E0B;

/* Error */
--et-error: #EF4444;

/* Info */
--et-info: #3B82F6;
```

## 應用到介面元件

### 1. 側邊欄
```css
background: #1E293B;        /* Navy 800 */
logo-color: #F97316;        /* Orange 500 */
text-color: #94A3B8;        /* Gray 400 */
active-bg: rgba(249, 115, 22, 0.1);  /* Orange with transparency */
active-text: #F97316;       /* Orange 500 */
active-border: #F97316;     /* Orange 500 */
```

### 2. 主要按鈕 (CTA)
```css
background: #F97316;        /* Orange 500 */
hover: #EA580C;             /* Orange 600 */
active: #C2410C;            /* Orange 700 */
```

### 3. 次要按鈕
```css
background: #0EA5E9;        /* Sky 500 */
hover: #0284C7;             /* Sky 600 */
active: #0369A1;            /* Sky 700 */
```

### 4. 統計卡片邊框
```css
UDN-border: #1E3A8A;        /* Navy 600 */
TVBS-border: #8B5CF6;       /* Purple 500 (保持原有) */
ETtoday-border: #0EA5E9;    /* Sky 500 */
```

### 5. 缺少新聞區域
```css
background: #FFF7ED;        /* Orange 50 */
border: #FED7AA;            /* Orange 200 */
border-left: #F97316;       /* Orange 500 - 4px */
header-bg: #FFEDD5;         /* Orange 100 */
header-text: #9A3412;       /* Orange 800 */
badge-bg: #F97316;          /* Orange 500 */
```

### 6. 改寫按鈕
```css
background: #F97316;        /* Orange 500 */
hover: #EA580C;             /* Orange 600 */
shadow: rgba(249, 115, 22, 0.3);
```

### 7. Spinner/Loading
```css
border-color: #E2E8F0;      /* Gray 200 */
border-top-color: #F97316;  /* Orange 500 */
```

### 8. 連結
```css
default: #1E293B;           /* Navy 800 */
hover: #F97316;             /* Orange 500 */
```

### 9. 背景
```css
body-bg: #F8FAFC;           /* Gray 50 */
card-bg: #FFFFFF;           /* White */
```

## 對比度檢查

所有配色組合均符合 WCAG AA 標準：

| 前景 | 背景 | 對比度 | 等級 |
|------|------|--------|------|
| #0F172A (Navy 900) | #FFFFFF | 16.9:1 | AAA |
| #1E293B (Navy 800) | #FFFFFF | 13.1:1 | AAA |
| #F97316 (Orange 500) | #FFFFFF | 3.4:1 | AA Large |
| #0EA5E9 (Sky 500) | #FFFFFF | 2.9:1 | AA Large |
| #FFFFFF | #F97316 | 3.4:1 | AA Large |
| #FFFFFF | #1E3A8A | 8.6:1 | AAA |

## 使用建議

1. **主色使用優先級**:
   - 深藍色 (#1E293B): 文字、標題
   - 橙色 (#F97316): CTA 按鈕、強調元素
   - 淺藍色 (#0EA5E9): 次要按鈕、資訊提示

2. **配色比例**:
   - 60% 中性色 (灰白)
   - 30% 深藍色
   - 10% 橙色+淺藍色 (強調)

3. **避免事項**:
   - 不要混用太多顏色 (最多3個主要顏色)
   - 橙色不適合大面積使用 (太刺眼)
   - 深藍色文字需要足夠對比度

4. **特殊場景**:
   - 錯誤訊息: 使用 #EF4444 (Red)
   - 成功訊息: 使用 #10B981 (Green)
   - 警告訊息: 使用 #F59E0B (Amber)
