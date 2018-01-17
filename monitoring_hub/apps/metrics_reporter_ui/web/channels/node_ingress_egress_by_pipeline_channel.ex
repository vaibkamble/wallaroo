defmodule MetricsReporterUI.NodeIngressEgressByPipelineChannel do
	use Phoenix.Channel
	alias MonitoringHubUtils.MessageLog

	def join("node-ingress-egress-by-pipeline:" <> _metric_name, _message, socket) do
		send(self(), :after_join)
    {:ok, socket}
	end

  def handle_info(:after_join, socket) do
    push_initial_throughputs(socket)
    {:noreply, socket}
  end

  defp push_initial_throughputs(socket) do
    start_time = :os.system_time(:seconds) - 300
    "node-ingress-egress-by-pipeline:" <> pipeline_key = socket.topic
    log_name = "category:node-ingress-egress-by-pipeline::cat-name:#{pipeline_key}::total-throughput:last-1-sec"
    throughputs = get_throughputs(log_name, start_time)
    throughputs_msg = %{pipeline_key: pipeline_key, data: throughputs}
    event = "initial-total-throughputs:last-1-sec"
    push socket, event, throughputs_msg
  end

  defp get_throughputs(log_name, start_time) do
    :ok = MessageLog.Supervisor.lookup_or_create(log_name)
    throughputs = MessageLog.get_logs(log_name, [start_time: start_time])
    List.delete_at(throughputs, -1)
  end
end
