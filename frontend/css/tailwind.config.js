// Tailwind ayarları. CSS'i yeniden üretmek için: css/derle.bat (Node.js gerekir)
module.exports = {
    content: ['../index.html', '../js/**/*.js'],
    theme: {
        extend: {
            colors: {
                'deneyap-red': { 50: '#FFF1F1', 100: '#FFE0E0', 200: '#FFC7C7', 300: '#FFA0A0', 400: '#FF6B6B', 500: '#DC2626', 600: '#C41E1E', 700: '#A31818', 800: '#871515', 900: '#6F1414' },
                'deneyap-blue': { 50: '#EFF6FF', 100: '#DBEAFE', 200: '#BFDBFE', 300: '#93C5FD', 400: '#60A5FA', 500: '#2563EB', 600: '#1D4ED8', 700: '#1E40AF', 800: '#1E3A8A', 900: '#1E3357' },
                'deneyap-yellow': { 50: '#FFFBEB', 100: '#FEF3C7', 200: '#FDE68A', 300: '#FCD34D', 400: '#FBBF24', 500: '#EAB308', 600: '#CA8A04', 700: '#A16207', 800: '#854D0E', 900: '#713F12' },
            },
            fontFamily: { inter: ['Inter', 'system-ui', 'sans-serif'] },
            animation: {
                'fade-in': 'fadeIn 0.5s ease-out',
                'slide-up': 'slideUp 0.4s ease-out',
                'slide-down': 'slideDown 0.3s ease-out',
                'scale-in': 'scaleIn 0.3s ease-out',
            },
            keyframes: {
                fadeIn: { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
                slideUp: { '0%': { transform: 'translateY(20px)', opacity: '0' }, '100%': { transform: 'translateY(0)', opacity: '1' } },
                slideDown: { '0%': { transform: 'translateY(-10px)', opacity: '0' }, '100%': { transform: 'translateY(0)', opacity: '1' } },
                scaleIn: { '0%': { transform: 'scale(0.95)', opacity: '0' }, '100%': { transform: 'scale(1)', opacity: '1' } },
            },
        },
    },
    plugins: [],
};
