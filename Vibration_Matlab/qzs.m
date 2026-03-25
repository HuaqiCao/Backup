clear; clc;

%% 目标无量纲参数
delta_hat_target = 0.5;      % δ̂ = δ / sqrt(a^2 + h1^2)
a_hat_target     = 0.755;    % â = a / sqrt(a^2 + h1^2)
alpha_target     = 0.942;    % α = k1/k2
alpha1_target    = 0.501;    % α₁ = k3/k2
gamma_target     = 2.143;    % γ = h/d
fprintf('目标无量纲参数:\n');
fprintf('  δ̂ = %.3f, â = %.3f, α = %.3f, α₁ = %.3f, γ = %.3f\n\n', ...
    delta_hat_target, a_hat_target, alpha_target, alpha1_target, gamma_target);

%% 物理参数限制（补充实际的一些空间限制）
k1_range = 100:200:900;      % 上斜弹簧刚度 N/m
h_range  = 0.10:0.05:0.30;   % 中间斜弹簧高度 m
h1_range = 0.14:0.05:0.40;   % 上斜弹簧高度 m
fprintf('总组合数: %d\n\n', length(k1_range) * length(h_range) * length(h1_range));
fprintf('遍历结果（物理量已转换为 mm）:\n');
fprintf('========================================================================================================================================================\n');
fprintf(' k1(N/m) | h(mm) | h1(mm) | k2(N/m) | k3(N/m) | a(mm) | d(mm) | delta(mm) | ρ | â实际 | â误差 %% | γ实际 | γ误差 %% | α实际 | α₁实际 | δ̂实际 | δ̂误差 %%\n');
fprintf('--------------------------------------------------------------------------------------------------------------------------------------------------------\n');

figure('Color', 'w', 'Position', [100, 100, 1000, 600]);
colors = lines(length(k1_range));
color_idx = 1;
h_iterated = []; 
iter_legend_str = ''; 
y_hat = linspace(-10, 10, 1000); 

for k1 = k1_range
    for h = h_range
        for h1 = h1_range
            % 用目标无量纲参数计算具体的初始条件
            d = h / gamma_target;                          
            a = (a_hat_target / sqrt(1 - a_hat_target^2)) * h1;  
            delta = delta_hat_target * sqrt(a^2 + h1^2);             
            k2 = k1 / alpha_target;                        
            k3 = alpha1_target * k2;    

            % 参数误差
            alpha_actual    = k1 / k2;                      
            alpha1_actual   = k3 / k2;                      
            a_hat_actual    = a / sqrt(a^2 + h1^2);         
            gamma_actual    = h / d;                        
            delta_hat_actual = delta / sqrt(a^2 + h1^2);    
            rho = (1 - a_hat_actual^2) / (gamma_actual - 1)^2;
            
            delta_hat1 = 1 - sqrt(1 + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho) + rho) + delta_hat_actual;
            delta_hat2 = 1 - sqrt(1 + 4*sqrt(1 - a_hat_actual^2)*sqrt(rho) + 4*rho) + delta_hat_actual;
            
            % 打印输出
            err_delta = abs(delta_hat_actual - delta_hat_target) / delta_hat_target * 100;
            fprintf('%8.1f | %5.1f | %5.1f | %7.1f | %7.1f | %5.1f | %5.1f | %9.2f | %.3f |   %.3f   |   %.2f   |    %.3f     |   %.2f   | %.3f | %.3f | %.3f |   %.2f\n', ...
                k1, h*1000, h1*1000, k2, k3, a*1000, d*1000, delta*1000, rho, a_hat_actual, 0, gamma_actual, 0, alpha_actual, alpha1_actual, delta_hat_actual, err_delta);
            
            x_e_hat = sqrt(1 - a_hat_actual^2) + sqrt(rho);
            y_hat = linspace(-10, 10, 1000); 
            K_hat = zeros(size(y_hat));
            
            for i = 1:length(y_hat)
                xi = x_e_hat + y_hat(i);
                P1 = sqrt(1 - a_hat_actual^2) - xi;
                P2 = 1 - 2*sqrt(1 - a_hat_actual^2)*xi + xi^2;
                P3 = 1 + delta_hat_actual;
                P4 = sqrt(1 - a_hat_actual^2 + rho + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho)) - xi;
                P5 = 1 + rho + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho) - 2*sqrt(1 - a_hat_actual^2 + rho + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho))*xi + xi^2;
                P6 = sqrt(1 + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho) + rho) + delta_hat1;
                P7 = sqrt(1 - a_hat_actual^2) + 2*sqrt(rho) - xi;
                P8 = 1 + 4*sqrt(1 - a_hat_actual^2)*sqrt(rho) + 4*rho - 2*(sqrt(1 - a_hat_actual^2) + 2*sqrt(rho))*xi + xi^2;
                P9 = sqrt(1 + 4*sqrt(1 - a_hat_actual^2)*sqrt(rho) + 4*rho) + delta_hat2;
                dP1 = -1; dP4 = -1; dP7 = -1;
                dP2 = -2*sqrt(1 - a_hat_actual^2) + 2*xi;
                dP5 = -2*sqrt(1 - a_hat_actual^2 + rho + 2*sqrt(1 - a_hat_actual^2)*sqrt(rho)) + 2*xi;
                dP8 = -2*(sqrt(1 - a_hat_actual^2) + 2*sqrt(rho)) + 2*xi;
                dN1 = -2 * alpha_actual * (1 - P3 * P2^(-0.5)) * dP1 - alpha_actual * P1 * P2^(-1.5) * P3 * dP2;
                dN3 = -2 * alpha1_actual * (1 - P6 * P5^(-0.5)) * dP4 - alpha1_actual * P4 * P5^(-1.5) * P6 * dP5;
                dN5 = -2 * alpha_actual * (1 - P9 * P8^(-0.5)) * dP7 - alpha_actual * P7 * P8^(-1.5) * P9 * dP8;
                K_hat(i) = 1 + dN1 + dN3 + dN5;
            end
            
            h_line = plot(y_hat, K_hat, 'Color', colors(color_idx,:), 'LineWidth', 3);
            hold on;
            
            if isempty(h_iterated)
            h_iterated = h_line;
            iter_legend_str = sprintf('$\\hat{a}=%.3f, \\hat{\\delta}=%.3f, \\gamma=%.3f, \\alpha=%.3f, \\alpha_1=%.3f$', ...
            a_hat_target, delta_hat_target, gamma_target, alpha_target, alpha1_target);
            end
        end
    end
    color_idx = color_idx + 1;
end

%% 计算目标曲线 
test_params = [0.700, 0.875, 1.728;
               0.600, 0.805, 1.970]; 

h_targets = [];
target_legends = {};
test_colors = {'b--', 'r--'}; 

for j = 1:size(test_params, 1)
    d_hat = test_params(j,1); a_hat = test_params(j,2); g = test_params(j,3);
    
    Delta = sqrt(1 + a_hat^2*g^2 - 2*a_hat^2*g); 
    Delta1 = (1 + d_hat)*(g - 1);
    Delta2 = (1 + d_hat)*(g - 1)^3;
    C1 = 6*(1 + d_hat)* a_hat^(-3)/(-12 * Delta2/Delta^3 + 72*Delta2*(1 - a_hat^2)/Delta^5 - 60*Delta2*(1 - a_hat^2)^2/Delta^7);
    alpha1_calc = -1/(C1*(4-4*Delta1/Delta + 4*(1-a_hat^2)*Delta1/Delta^3)+ 2*(1-(1+d_hat)/a_hat));
    alpha_calc = C1 * alpha1_calc;
    
    K_hat_target = zeros(size(y_hat));
    rho_target = (1 - a_hat^2) / (g - 1)^2;
    delta_hat1_target = 1 - sqrt(1 + 2*sqrt(1 - a_hat^2)*sqrt(rho_target) + rho_target) + d_hat;
    delta_hat2_target = 1 - sqrt(1 + 4*sqrt(1 - a_hat^2)*sqrt(rho_target) + 4*rho_target) + d_hat;
    x_e_hat_target = sqrt(1 - a_hat^2) + sqrt(rho_target);
    
    for i = 1:length(y_hat)
        xi = x_e_hat_target + y_hat(i);
        P1 = sqrt(1 - a_hat^2) - xi; P2 = 1 - 2*sqrt(1 - a_hat^2)*xi + xi^2; P3 = 1 + d_hat;
        P4 = sqrt(1 - a_hat^2 + rho_target + 2*sqrt(1 - a_hat^2)*sqrt(rho_target)) - xi;
        P5 = 1 + rho_target + 2*sqrt(1 - a_hat^2)*sqrt(rho_target) - 2*sqrt(1 - a_hat^2 + rho_target + 2*sqrt(1 - a_hat^2)*sqrt(rho_target))*xi + xi^2;
        P6 = sqrt(1 + 2*sqrt(1 - a_hat^2)*sqrt(rho_target) + rho_target) + delta_hat1_target;
        P7 = sqrt(1 - a_hat^2) + 2*sqrt(rho_target) - xi;
        P8 = 1 + 4*sqrt(1 - a_hat^2)*sqrt(rho_target) + 4*rho_target - 2*(sqrt(1 - a_hat^2) + 2*sqrt(rho_target))*xi + xi^2;
        P9 = sqrt(1 + 4*sqrt(1 - a_hat^2)*sqrt(rho_target) + 4*rho_target) + delta_hat2_target;
        dP2 = -2*sqrt(1 - a_hat^2) + 2*xi;
        dP5 = -2*sqrt(1 - a_hat^2 + rho_target + 2*sqrt(1 - a_hat^2)*sqrt(rho_target)) + 2*xi;
        dP8 = -2*(sqrt(1 - a_hat^2) + 2*sqrt(rho_target)) + 2*xi;
        dN1 = -2 * alpha_calc * (1 - P3 * P2^(-0.5)) * (-1) - alpha_calc * P1 * P2^(-1.5) * P3 * dP2;
        dN3 = -2 * alpha1_calc * (1 - P6 * P5^(-0.5)) * (-1) - alpha1_calc * P4 * P5^(-1.5) * P6 * dP5;
        dN5 = -2 * alpha_calc * (1 - P9 * P8^(-0.5)) * (-1) - alpha_calc * P7 * P8^(-1.5) * P9 * dP8;
        K_hat_target(i) = 1 + dN1 + dN3 + dN5;
    end
    h_targets(j) = plot(y_hat, K_hat_target, test_colors{j}, 'LineWidth', 3);
    target_legends{j} = sprintf('$\\hat{a}=%.3f, \\hat{\\delta}=%.3f, \\gamma=%.3f, \\alpha=%.3f, \\alpha_1=%.3f$', ...
    a_hat, d_hat, g, alpha_calc, alpha1_calc);
end

% 图例
legend([h_targets, h_iterated], [target_legends, {iter_legend_str}], ...
    'Interpreter', 'latex', 'Location', 'northeast', 'FontSize', 16);
set(legend, 'Position', [0.45, 0.75, 0.2, 0.1]);
set(h_iterated, 'Color', [0.4660 0.6740 0.1880], 'LineStyle', '-', 'LineWidth', 3);
set(gca, 'FontSize', 16);
xlabel('$\hat{y}$', 'Interpreter', 'latex', 'FontSize', 22);
ylabel('$\hat{K}$', 'Interpreter', 'latex', 'FontSize', 22);
xticks([-0.8, -0.5, -0.3, 0, 0.3, 0.5, 0.8]);

title('Stiffness curves comparison of QZS', 'FontSize', 26, 'Interpreter', 'latex');
grid on; box on; xlim([-0.8, 0.8]); ylim([-0, 1.5]);