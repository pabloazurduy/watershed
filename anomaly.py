import pandas as pd
from typing import List 
from prophet import Prophet
from prophet.diagnostics import generate_cutoffs
from others import suppress_stdout_stderr
import plotly.graph_objs as go
from multiprocessing import Pool 

def plot_outliers(outliers_df:pd.DataFrame, variable_name:str, gauge_name:str, basin_id:int) -> None:
    # fig.data = []
    fig = go.Figure([
        go.Scatter(
            name='Measurement',
            x=outliers_df['ds'],
            y=outliers_df['y'],
            mode='lines',
            line=dict(color='rgb(31, 119, 180)'),
        ),
        go.Scatter(
            name='Upper Bound',
            x=outliers_df['ds'],
            y=outliers_df['yhat_upper'],
            mode='lines',
            marker=dict(color="#444"),
            line=dict(width=0),
            showlegend=False
        ),
        go.Scatter(
            name='Lower Bound',
            x=outliers_df['ds'],
            y=outliers_df['yhat_lower'],
            marker=dict(color="#444"),
            line=dict(width=0),
            mode='lines',
            fillcolor='rgba(68, 68, 68, 0.3)',
            fill='tonexty',
            showlegend=False
        ),
        go.Scatter(
            name = 'Outliers',
            x=outliers_df[outliers_df['anomaly_flag']]['ds'],
            y=outliers_df[outliers_df['anomaly_flag']]['y'],
            line=dict(color='red'),
            mode='markers'
        ),
    ])
    fig.update_layout(title=f'Anomaly Flag, {gauge_name = } [id={basin_id}], var = {variable_name}')    
    fig.write_image(f"anomaly_plots/{variable_name}_{basin_id}.png", scale=6, width=1400, height=800)

def find_outliers(sub_df:pd.DataFrame, 
                  variable_name:str,
                  gauge_name:str,
                  basin_id:int,
                  horizon_test_yrs:int = 3, # rolling window on where to predict/find anomalies
                  train_yrs:int = 3, 
                  confidence_interval_width = 0.99 # customize to make the model more or less sensitive 
                  ) -> pd.DataFrame:
    
    ts_df = sub_df[['date_ts', variable_name]].copy()
    ts_df.rename({variable_name:'y',
                  'date_ts':'ds'}, axis=1, inplace=True)
    test_size = 365 * horizon_test_yrs
    train_size = 365 * train_yrs
    if len(ts_df) <= (train_size + test_size):
        print(f'Skipping {basin_id}')
        return None                
    horizon = pd.Timedelta(f'{test_size} days')
    period = horizon 
    cuoffs_list = generate_cutoffs(ts_df, 
                                   horizon=horizon,
                                   period=period, 
                                   initial =pd.Timedelta(f'{train_yrs*365} days'),
                                )    
    forecast_df_list:List[pd.DataFrame] = []
    for cutoff_date in cuoffs_list:
        fold_ts_df = ts_df[ts_df['ds']<=cutoff_date].copy()
        with suppress_stdout_stderr():
            model = Prophet(n_changepoints = 0, # force no changepoints 
                            weekly_seasonality=False,
                            interval_width=confidence_interval_width,
                            )
            model.fit(fold_ts_df)
            future = model.make_future_dataframe(periods=test_size)
            forecast = model.predict(future)
        # remove outliers from ts_df
        next_fold_ds = ts_df[(ts_df['ds']> cutoff_date) & 
                             (ts_df['ds']<= cutoff_date +horizon)].copy()
        forecasted_fold_ds = pd.merge(next_fold_ds, forecast, how='left', on='ds')
        forecasted_fold_ds['anomaly_flag'] = ((forecasted_fold_ds['y'] > forecasted_fold_ds['yhat_upper'])  
                                              # | (forecasted_fold_ds['y'] < forecasted_fold_ds['yhat_lower'])
                                              )
        forecast_df_list.append(forecasted_fold_ds)
        # remove outliers
        ts_df.loc[ts_df['ds'].isin(forecasted_fold_ds[forecasted_fold_ds['anomaly_flag']]['ds']), 'y'] = None 
        print(f'{basin_id = } {cutoff_date.strftime("%Y-%m-%d")} num_outliers = {forecasted_fold_ds["anomaly_flag"].sum()}')
    outliers_df = pd.concat(forecast_df_list)
    outliers_df.dropna(inplace=True)
    plot_outliers(outliers_df, 
                  variable_name=variable_name,
                  basin_id=basin_id, 
                  gauge_name=gauge_name)
    outliers_df['basin_id'] = basin_id
    outliers_df = outliers_df[['basin_id', 'ds', 'anomaly_flag']].copy()
    outliers_df.rename({'y':variable_name,
                        'ds':'date_ts',
                        'anomaly_flag':f'{variable_name}_extreme'}, axis=1, inplace=True)
    return outliers_df


if __name__ == "__main__":
    flux_df = pd.read_csv('challenge_watershed/flux.csv')
    flux_df['date_ts'] = pd.to_datetime(flux_df['date'])
    outliers_res_list:List[pd.DataFrame] = []
    res_list = []
    basin_ids = flux_df['basin_id'].unique()
    with Pool(processes=8) as pool:
        for cod_station in basin_ids: 
            gauge_name = flux_df[flux_df['basin_id'] == cod_station]['gauge_name'].iat[0]
            for variable_name in ['flux','precip','temp_max']:
                print(f'starting {cod_station}{variable_name}')
                sub_df = flux_df[(flux_df['basin_id'] == cod_station)][['flux','precip','temp_max','date_ts']].copy()
                # outliers_df = find_outliers(sub_df, 
                #                             variable_name=variable_name, 
                #                             gauge_name=gauge_name, 
                #                             basin_id = cod_station)
                res = pool.apply_async(find_outliers, kwds={'sub_df':sub_df,
                                                             'variable_name':variable_name,
                                                             'gauge_name':gauge_name, 
                                                             'basin_id':cod_station})
                res_list.append(res)
        outliers_res_list = [res.get() for res in res_list]
    outliers_res_list = [df for df in outliers_res_list if df is not None]
    out_df_dic = {bid:[] for bid in basin_ids}
    for df in outliers_res_list:
        out_df_dic[df['basin_id'].iat[0]].append(df)
    
    all_basin_flags = []
    for bid in out_df_dic.keys():
        if len(out_df_dic[bid])>0:
            print(bid)
            basin_flags_list = [df.reset_index(drop=True) for df in  out_df_dic[bid]]
            basin_flags = pd.concat(basin_flags_list, axis = 1).T.drop_duplicates().T
            basin_flags.dropna(inplace=True)
            basin_flags = basin_flags.loc[:,~basin_flags.columns.duplicated()].copy()
            print(len(basin_flags.columns))
            all_basin_flags.append(basin_flags)

    all_basin_flags_ri = [df.reset_index(drop=True) for df in all_basin_flags if len(df.columns)==5]
    all_basin_flags_df = pd.concat(all_basin_flags_ri, axis=0)
    all_basin_flags_df.to_csv('anomaly_flag.csv', index=False)