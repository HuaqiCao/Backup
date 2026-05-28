path = '~/Desktop/Figures';
if ~exist(path, 'dir'), mkdir(path); end

M = 2; %kg
g = 9.81;
c = 153.1-(M*g)/0.3843;

for a=24:44
    for d=55:80
        y = linspace(-100, 100, 1000);  % 设置x的范围和点数
        f = -2.*(119.2-sqrt((a+y).^2+d^2)).*(a+y).*0.362./sqrt((a+y).^2+d^2)+2.*(119.2-sqrt((-y).^2+d^2)).*(-y).*0.1825./sqrt((-y).^2+d^2)+2.*(119.2-sqrt((a-y).^2+d^2)).*(a-y).*0.362./sqrt((a-y).^2+d^2)+(153.1-c+y).*0.3843;

        fig = figure('Visible', 'off');
        plot(y, f, 'LineWidth', 2);
        grid on;
        xlabel('y/mm');
        ylabel('f/N');
        title(sprintf('f-y图像, a=%.1fmm, d=%.1fmm,c=%0.1f', a, d,c));

        exportgraphics(fig, sprintf('%s/fig_a%d_d%d.png', path, a, d), 'Resolution', 300);
        close(fig);
    end
end