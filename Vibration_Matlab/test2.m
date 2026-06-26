d=20;
l=30;
k1=1;
k2=2*(l/d-1);
%f=2*k1*(l-sqrt(x^2+d^2))*x/sqrt(x^2+d^2)-k2*x;

x = linspace(-8, 8, 1000); 

f = 2 .* k1 .* (l - sqrt(x.^2 + d.^2)) .* x ./ sqrt(x.^2 + d.^2) - k2 .* x;

figure;
plot(x, f, 'b-', 'LineWidth', 2);
grid on;
xlabel('位移 x');
ylabel('恢复力 f');
ylim([-4 4]);
title('非线性弹簧力-位移曲线');