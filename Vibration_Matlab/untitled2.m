d=20.96;
a=21.26;
l1=49.8;
l2=49.8;
k1=0.3785;
k2=0.2406;
k3=0.2013;
k4=0.03;
x1=-0.4:0.0001:0.4;
y1=zeros(size(x1));
z1=zeros(size(x1))
for i=1:length(x1)
    x=x1(i);
    fun = @(y) my_equations(y,k1,k2,k3,l1,l2,a,d)-x;
    y_solution = fzero(fun, 0);
    y1(i)=y_solution+(x-k2*y_solution)/k4;
end
figure;
plot(y1, x1, 'b-', 'LineWidth', 2);
grid on;
xlabel('x'); ylabel('y');
function F=my_equations(x,k1,k2,k3,l1,l2,a,d)
F= 3.*k1.*(l1 - sqrt((a-x).^2 + d.^2)) ./ sqrt((a-x).^2 + d.^2) .* (a-x) ...
    - 3.*k1.*(l1 - sqrt((a+x).^2 + d.^2)) ./ sqrt((a+x).^2 + d.^2) .* (a+x) ...
    - 3 .* k3 .* (l2 - sqrt(x.^2 + d.^2)) .* x ./ sqrt(x.^2 + d.^2)+ k2.*x;
end