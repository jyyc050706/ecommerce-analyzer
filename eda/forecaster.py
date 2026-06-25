"""
时序预测模块 — 基于 Prophet 的日交易量预测

调用链：日交易量数据 → Prophet.fit → 未来预测 + 趋势分解 + 评估指标
用途：看板预测页、异常检测的 Prophet 残差层
"""

import pandas as pd
import numpy as np
from prophet import Prophet
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional


class Forecaster:
    """Prophet 时序预测封装

    Parameters
    ----------
    df : pd.DataFrame
        含日期和目标值的 DataFrame，列名通过 date_col / target_col 指定
    date_col : str
        日期列名，默认 'ds'
    target_col : str
        目标值列名，默认 'y'
    freq : str
        数据频率，'D' 表示日级
    changepoint_prior_scale : float
        趋势突变点灵敏度，默认 0.05
    seasonality_mode : str
        'additive' 或 'multiplicative'，默认 'additive'
    """

    def __init__(
        self,
        df: pd.DataFrame,
        date_col: str = "ds",
        target_col: str = "y",
        freq: str = "D",
        changepoint_prior_scale: float = 0.05,
        seasonality_mode: str = "additive",
    ):
        self.df = df.copy()
        self.date_col = date_col
        self.target_col = target_col
        self.freq = freq
        self.changepoint_prior_scale = changepoint_prior_scale
        self.seasonality_mode = seasonality_mode

        # 标准化列名为 Prophet 要求的 ds / y
        self._data = self.df[[date_col, target_col]].rename(
            columns={date_col: "ds", target_col: "y"}
        )
        self._data["ds"] = pd.to_datetime(self._data["ds"])

        data_days = (self._data["ds"].max() - self._data["ds"].min()).days
        use_yearly = data_days >= 365 * 2  # 至少 2 年才开年周期性

        self._model = Prophet(
            yearly_seasonality=use_yearly,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=changepoint_prior_scale,
            seasonality_mode=seasonality_mode,
        )
        self._fitted = False
        self._forecast = None

    def fit(self) -> "Forecaster":
        """拟合模型"""
        self._model.fit(self._data)
        self._fitted = True
        return self

    def predict(self, periods: int = 30) -> pd.DataFrame:
        """预测未来 N 期

        Returns
        -------
        pd.DataFrame
            ds, yhat, yhat_lower, yhat_upper
        """
        if not self._fitted:
            raise RuntimeError("请先调用 fit()")
        future = self._model.make_future_dataframe(periods=periods, freq=self.freq)
        self._forecast = self._model.predict(future)
        return self._forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]

    def forecast_df(self) -> pd.DataFrame:
        """返回完整预测结果（历史 + 未来 + 各分量）"""
        if self._forecast is None:
            self.predict()
        return self._forecast

    def get_model(self) -> Prophet:
        """获取底层 Prophet 模型（供异常检测共享）"""
        if not self._fitted:
            raise RuntimeError("请先调用 fit()")
        return self._model

    def plot(self, title: str = "时序预测") -> go.Figure:
        """Plotly 交互预测图：历史值 + 预测 + 置信区间"""
        if self._forecast is None:
            self.predict()

        fc = self._forecast
        fig = go.Figure()

        # 历史实际值
        fig.add_trace(
            go.Scatter(
                x=self._data["ds"],
                y=self._data["y"],
                mode="markers",
                name="实际值",
                marker=dict(color="#60a5fa", size=4),
            )
        )

        # 预测值
        fig.add_trace(
            go.Scatter(
                x=fc["ds"],
                y=fc["yhat"],
                mode="lines",
                name="预测值",
                line=dict(color="#f59e0b", width=2),
            )
        )

        # 置信区间
        fig.add_trace(
            go.Scatter(
                x=pd.concat([fc["ds"], fc["ds"][::-1]]),
                y=pd.concat([fc["yhat_upper"], fc["yhat_lower"][::-1]]),
                fill="toself",
                fillcolor="rgba(245,158,11,0.1)",
                line=dict(color="rgba(255,255,255,0)"),
                name="95% 置信区间",
            )
        )

        fig.update_layout(
            title=title,
            xaxis_title="日期",
            yaxis_title="交易量",
            template="plotly_dark",
            hovermode="x unified",
        )
        return fig

    def components_plot(self) -> go.Figure:
        """趋势 + 周季节性分解图"""
        if self._forecast is None:
            self.predict()

        fc = self._forecast
        # 找到可用分量
        component_names = ["trend"]
        if "weekly" in fc.columns:
            component_names.append("weekly")

        if "yearly" in fc.columns:
            component_names.append("yearly")

        n_components = len(component_names)
        fig = make_subplots(rows=n_components, cols=1, subplot_titles=component_names)

        for i, comp in enumerate(component_names):
            row = i + 1
            if comp == "weekly":
                # 取最后一周的 weekly 分量
                weekly_data = fc[["ds", "weekly"]].drop_duplicates(subset="weekly")
                dow_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
                x_vals = dow_labels[: len(weekly_data)]
                fig.add_trace(
                    go.Bar(x=x_vals, y=weekly_data["weekly"].values, name=comp),
                    row=row,
                    col=1,
                )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=fc["ds"],
                        y=fc[comp],
                        mode="lines",
                        name=comp,
                        line=dict(width=2),
                    ),
                    row=row,
                    col=1,
                )

        fig.update_layout(
            title="趋势与季节性分解",
            template="plotly_dark",
            showlegend=False,
            height=250 * n_components,
        )
        return fig

    def metrics(self) -> dict:
        """回测评估指标：MAE / RMSE / MAPE"""
        if not self._fitted:
            raise RuntimeError("请先调用 fit()")

        # 对历史数据做 in-sample 预测
        hist_pred = self._model.predict(self._data[["ds"]])
        y_true = self._data["y"].values
        y_pred = hist_pred["yhat"].values

        mae = np.mean(np.abs(y_true - y_pred))
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
        mape = np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 1))) * 100

        return {
            "MAE": round(mae, 2),
            "RMSE": round(rmse, 2),
            "MAPE": round(mape, 2),
        }
