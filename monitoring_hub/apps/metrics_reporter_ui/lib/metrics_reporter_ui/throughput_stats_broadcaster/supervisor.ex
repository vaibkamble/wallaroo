defmodule MetricsReporterUI.ThroughputStatsBroadcaster.Supervisor do
	use Supervisor

  alias MetricsReporterUI.ThroughputStatsBroadcaster.Worker
  @name MetricsReporterUI.ThroughputStatsBroadcaster.Supervisor

  def start_link do
    Supervisor.start_link(__MODULE__, [], name: @name)
  end

  def start_worker([log_name: _log_name, interval_key: _interval_key,
    pipeline_key: _pipeline_key, app_name: _app_name, category: _category, stats_interval: _stats_interval] = args) do
    Supervisor.start_child(@name, [args])
  end

  def find_or_start_worker([log_name: log_name, interval_key: interval_key,
    pipeline_key: _pipeline_key, app_name: _app_name, category: _category, stats_interval: _stats_interval] = args) do
    case :gproc.where({:n, :l, {:tsb_worker, message_log_name(log_name, interval_key)}}) do
      :undefined ->
        start_worker(args)
      pid ->
        {:ok, pid}
    end
  end

  def init([]) do
    children = [
      worker(Worker, [], restart: :temporary)
    ]

    supervise(children, strategy: :simple_one_for_one)
  end

  defp message_log_name(pipeline_key, interval_key) do
    "log:" <> pipeline_key <> "::interval-key:" <> interval_key
  end
end
